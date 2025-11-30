# routers/search_hybrid.py
import os, json, math
from typing import List, Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint, confloat

from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# =========================================
# Router
# =========================================
router = APIRouter(prefix="/api/search", tags=["hybrid-search"])

# =========================================
# Config loader
# =========================================
def load_config() -> dict:
    cfg_path = os.getenv("CONFIG_PATH") or os.path.join(os.path.dirname(__file__), "..", "config.json")
    cfg_path = os.path.abspath(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================================
# Embedding client & helpers
# =========================================
def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
    return AzureOpenAI(
        api_key=cfg["openai_api_key"],
        api_version=cfg["openai_api_version"],
        azure_endpoint=cfg["openai_endpoint"],
    )

def embed_query(azure_embed_client: AzureOpenAI, model: str, text: str, target_dim: int) -> List[float]:
    if not text or not str(text).strip():
        return [0.0] * target_dim
    resp = azure_embed_client.embeddings.create(model=model, input=[text])
    vec = resp.data[0].embedding
    if len(vec) < target_dim:
        vec = vec + [0.0] * (target_dim - len(vec))
    elif len(vec) > target_dim:
        vec = vec[:target_dim]
    return vec

# =========================================
# REST params for Azure AI Search
# =========================================
def _rest_search_url(cfg: dict, index_name: Optional[str] = None) -> str:
    service = cfg["search_service_name"]
    api_version = cfg["search_api_version"]
    index = index_name or cfg["index_name"]
    return f"https://{service}.search.windows.net/indexes('{index}')/docs/search?api-version={api_version}"

def _rest_headers(cfg: dict) -> Dict[str, str]:
    return {"Content-Type": "application/json", "api-key": cfg["search_api_key"]}

# =========================================
# Field selection (align with flatten_for_index)
# =========================================
STRUCT_FIELDS = [
    "org_name", "country", "address", "founded_year", "size", "industry", "is_DU_member", "website",
    "members_name", "members_title", "members_role",
    "facilities_name", "facilities_type", "facilities_usage",
    "capabilities", "projects", "awards", "services",
    "contacts_name", "contacts_email", "contacts_phone",
    "addresses", "notes", "page_from", "page_to",
]
BASE_FIELDS = ["id", "chunk_index", "content", "filepath"]
SELECT_FIELDS = BASE_FIELDS + STRUCT_FIELDS

# =========================================
# Vector-only & BM25-only via REST
# =========================================
def vector_topk_rest(cfg: dict, qvec: List[float], k: int, select_fields: List[str], index_name: Optional[str] = None) -> List[Dict[str, Any]]:
    url = _rest_search_url(cfg, index_name=index_name)
    headers = _rest_headers(cfg)
    body = {
        "select": ",".join(select_fields),
        "top": k,
        "search": None,
        "vectorQueries": [
            {"kind": "vector", "vector": qvec, "k": k, "fields": "content_vector"}
        ],
    }
    r = requests.post(url, headers=headers, data=json.dumps(body, allow_nan=False))
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {r.status_code} {r.text}")
    data = r.json()
    out = []
    for it in data.get("value", []):
        out.append({
            "id": it.get("id"),
            "score": it.get("@search.score", None),
            "doc": {f: it.get(f, None) for f in select_fields},
        })
    return out

def bm25_topk_rest(cfg: dict, query_text: str, k: int, select_fields: List[str], index_name: Optional[str] = None) -> List[Dict[str, Any]]:
    url = _rest_search_url(cfg, index_name=index_name)
    headers = _rest_headers(cfg)
    body = {
        "select": ",".join(select_fields),
        "top": k,
        "search": query_text,
        # 如需 semantic，可在标准层启用：
        # "queryType": "semantic",
        # "semanticConfiguration": "semantic-config",
    }
    r = requests.post(url, headers=headers, data=json.dumps(body, allow_nan=False))
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"BM25 search failed: {r.status_code} {r.text}")
    data = r.json()
    out = []
    for it in data.get("value", []):
        out.append({
            "id": it.get("id"),
            "score": it.get("@search.score", None),
            "doc": {f: it.get(f, None) for f in select_fields},
        })
    return out

# =========================================
# Score normalization & merge
# =========================================
def _minmax_norm(scores: List[Optional[float]]) -> List[float]:
    vals = [s for s in scores if isinstance(s, (int, float))]
    if not vals:
        return [0.0] * len(scores)
    mn, mx = min(vals), max(vals)
    if mx <= mn:
        return [1.0 if isinstance(s, (int, float)) else 0.0 for s in scores]
    out = []
    for s in scores:
        if isinstance(s, (int, float)):
            out.append((s - mn) / (mx - mn))
        else:
            out.append(0.0)
    return out

def merge_and_pick_top(vec_hits, bm_hits, alpha: float = 0.5, top_n: int = 3) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    vec_norms = _minmax_norm([h["score"] for h in vec_hits])
    bm_norms  = _minmax_norm([h["score"] for h in bm_hits])

    for h, nv in zip(vec_hits, vec_norms):
        did = h["id"]
        merged.setdefault(did, {
            "id": did,
            "vec_score_raw": None, "bm25_score_raw": None,
            "vec_score_norm": 0.0, "bm25_score_norm": 0.0,
            "doc": h["doc"]
        })
        merged[did]["vec_score_raw"] = h["score"]
        merged[did]["vec_score_norm"] = nv

    for h, nb in zip(bm_hits, bm_norms):
        did = h["id"]
        merged.setdefault(did, {
            "id": did,
            "vec_score_raw": None, "bm25_score_raw": None,
            "vec_score_norm": 0.0, "bm25_score_norm": 0.0,
            "doc": h["doc"]
        })
        merged[did]["bm25_score_raw"]  = h["score"]
        merged[did]["bm25_score_norm"] = nb
        if not merged[did].get("doc"):
            merged[did]["doc"] = h["doc"]

    rows = []
    for _, rec in merged.items():
        vecn = rec["vec_score_norm"]; bmn = rec["bm25_score_norm"]
        combined = alpha * vecn + (1.0 - alpha) * bmn
        row = {
            "id": rec["id"],
            "combined_score": combined,
            "vec_score_raw": rec["vec_score_raw"],
            "bm25_score_raw": rec["bm25_score_raw"],
            "vec_score_norm": vecn,
            "bm25_score_norm": bmn,
        }
        row.update(rec["doc"])
        rows.append(row)

    rows.sort(key=lambda x: x["combined_score"], reverse=True)
    return rows[:top_n]

# =========================================
# Pydantic models
# =========================================
class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="用户查询文本")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    kvec: int = Field(default=10, ge=1, le=50)
    kbm25: int = Field(default=10, ge=1, le=50)
    top_n: int = Field(default=3, ge=1, le=50)
    index_name: Optional[str] = Field(default=None, description="覆盖默认 index 名")
    embedding_model: Optional[str] = Field(default=None, description="覆盖默认 embedding 部署名")
    embedding_dimensions: Optional[int] = Field(default=None, description="覆盖默认 embedding 维度")
    select_extra: Optional[List[str]] = Field(default=None, description="附加 select 字段")
    # 是否截断 content 预览
    content_preview_chars: Optional[int] = Field(default=None, description="如设置则仅返回 content 前 N 字符")

class HybridSearchBatchRequest(BaseModel):
    queries: List[str] = Field(..., min_items=1, description="多条查询")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    kvec: int = Field(default=10, ge=1, le=50)
    kbm25: int = Field(default=10, ge=1, le=50)
    top_n: int = Field(default=3, ge=1, le=50)
    index_name: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    select_extra: Optional[List[str]] = None
    content_preview_chars: Optional[int] = None

# =========================================
# Core: single query
# =========================================
def _hybrid_query_core(
    query_text: str,
    cfg: dict,
    k_vec: int = 3,
    k_bm25: int = 3,
    alpha: float = 0.5,
    select_extra: Optional[List[str]] = None,
    index_name: Optional[str] = None,
    embedding_model: Optional[str] = None,
    embedding_dimensions: Optional[int] = None,
) -> List[Dict[str, Any]]:
    embed_dims = int(embedding_dimensions or cfg.get("embedding_dimensions", 1536))
    embed_model_use = embedding_model or cfg["embedding_model"]
    embed_client = build_azure_embed_client(cfg)
    qvec = embed_query(embed_client, embed_model_use, query_text, embed_dims)

    select_fields = list(SELECT_FIELDS)
    if select_extra:
        for f in select_extra:
            if f not in select_fields:
                select_fields.append(f)

    vec_hits = vector_topk_rest(cfg, qvec, k_vec, select_fields, index_name=index_name)
    bm_hits  = bm25_topk_rest(cfg, query_text, k_bm25, select_fields, index_name=index_name)
    top_rows = merge_and_pick_top(vec_hits, bm_hits, alpha=alpha, top_n=max(1, min(50, k_vec, k_bm25)))  # 先合并到 min(kvec,kbm25)
    return top_rows

def _clean_rows(rows: List[Dict[str, Any]], top_n: int, preview_chars: Optional[int]) -> List[Dict[str, Any]]:
    rows = rows[:top_n]
    cleaned = []
    import re
    def clean_content(text: str) -> str:
        if not text:
            return ""
        t = text
        # 去除 :unselected:、++、多余空行、装饰符号等
        t = re.sub(r":unselected:", "", t)
        t = re.sub(r"\+\+", "", t)
        t = re.sub(r"[-•=_*~#]{3,}", "", t)
        t = re.sub(r"[\.]{3,}", "...", t)
        t = re.sub(r"[\\|/]{2,}", "", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"\s+", " ", t)
        t = t.strip()
        return t

    for r in rows:
        out = {
            "id": r.get("id"),
            "chunk_index": r.get("chunk_index"),
            "filepath": r.get("filepath"),
            "content": r.get("content"),
            "combined_score": r.get("combined_score"),
            "vec_score_raw": r.get("vec_score_raw"),
            "bm25_score_raw": r.get("bm25_score_raw"),
            "vec_score_norm": r.get("vec_score_norm"),
            "bm25_score_norm": r.get("bm25_score_norm"),
        }
        # 结构化字段
        for f in STRUCT_FIELDS:
            out[f] = r.get(f, None)
        # content 清理和截断
        if isinstance(out["content"], str):
            c = clean_content(out["content"])
            if preview_chars is not None:
                out["content"] = c[:preview_chars] + (" ..." if len(c) > preview_chars else "")
            else:
                out["content"] = c
        cleaned.append(out)
    return cleaned

# =========================================
# Endpoints
# =========================================
@router.get("/health")
def health():
    try:
        cfg = load_config()
        # 粗查关键项
        for k in ["search_service_name", "search_api_version", "index_name", "openai_api_key", "openai_endpoint", "openai_api_version", "embedding_model"]:
            if k not in cfg:
                raise ValueError(f"Missing key in config: {k}")
        return {"ok": True, "service": cfg.get("search_service_name"), "default_index": cfg.get("index_name")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/hybrid")
def hybrid(req: HybridSearchRequest):
    try:
        cfg = load_config()
        rows = _hybrid_query_core(
            query_text=req.query,
            cfg=cfg,
            k_vec=req.kvec,
            k_bm25=req.kbm25,
            alpha=req.alpha,
            select_extra=req.select_extra,
            index_name=req.index_name,
            embedding_model=req.embedding_model,
            embedding_dimensions=req.embedding_dimensions,
        )
        # 只保留分数大于等于0.75的结果
        filtered_rows = [r for r in rows if r.get("combined_score", 0) >= 0.75]
        return {
            "ok": True,
            "query": req.query,
            "alpha": req.alpha,
            "kvec": req.kvec,
            "kbm25": req.kbm25,
            "top_n": req.top_n,
            "results": _clean_rows(filtered_rows, req.top_n, req.content_preview_chars),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hybrid_batch")
def hybrid_batch(req: HybridSearchBatchRequest):
    try:
        cfg = load_config()
        all_out = []
        for q in req.queries:
            rows = _hybrid_query_core(
                query_text=q,
                cfg=cfg,
                k_vec=req.kvec,
                k_bm25=req.kbm25,
                alpha=req.alpha,
                select_extra=req.select_extra,
                index_name=req.index_name,
                embedding_model=req.embedding_model,
                embedding_dimensions=req.embedding_dimensions,
            )
            all_out.append({
                "query": q,
                "results": _clean_rows(rows, req.top_n, req.content_preview_chars),
            })
        return {
            "ok": True,
            "alpha": req.alpha,
            "kvec": req.kvec,
            "kbm25": req.kbm25,
            "top_n": req.top_n,
            "items": all_out,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
