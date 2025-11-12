import os, sys, json
from typing import List, Dict, Any, Optional

import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI


# ========= 与入库一致：构造 Embedding 客户端 =========
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


# ========= 配置 / REST 基本参数 =========
def _rest_search_url(cfg: dict) -> str:
    service = cfg["search_service_name"]
    api_version = cfg["search_api_version"]
    index_name = cfg["index_name"]
    return f"https://{service}.search.windows.net/indexes('{index_name}')/docs/search?api-version={api_version}"

def _rest_headers(cfg: dict) -> Dict[str, str]:
    return {"Content-Type": "application/json", "api-key": cfg["search_api_key"]}


# ========= 选择字段（与你的 flatten_for_index 对齐）=========
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


# ========= 用 REST 做“只向量 topk” =========
def vector_topk_rest(cfg: dict, qvec: List[float], k: int, select_fields: List[str]) -> List[Dict[str, Any]]:
    url = _rest_search_url(cfg)
    headers = _rest_headers(cfg)
    body = {
        "select": ",".join(select_fields),
        "top": k,
        "search": None,  # 只向量检索
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": qvec,
                "k": k,
                "fields": "content_vector"
            }
        ]
    }
    r = requests.post(url, headers=headers, data=json.dumps(body))
    if r.status_code != 200:
        raise RuntimeError(f"Vector search failed: {r.status_code} {r.text}")
    data = r.json()
    out = []
    for it in data.get("value", []):
        out.append({
            "id": it.get("id"),
            "score": it.get("@search.score", None),
            "doc": {f: it.get(f, None) for f in select_fields}
        })
    return out

# ========= 用 REST 做“只 BM25 topk” =========
def bm25_topk_rest(cfg: dict, query_text: str, k: int, select_fields: List[str]) -> List[Dict[str, Any]]:
    url = _rest_search_url(cfg)
    headers = _rest_headers(cfg)
    body = {
        "select": ",".join(select_fields),
        "top": k,
        "search": query_text,   # 只 BM25
        # 如果需要 semantic rerank，可启用，目前Azure AI Search免费套餐无法使用：
        # "queryType": "semantic",
        # "semanticConfiguration": "semantic-config",
    }
    r = requests.post(url, headers=headers, data=json.dumps(body))
    if r.status_code != 200:
        raise RuntimeError(f"BM25 search failed: {r.status_code} {r.text}")
    data = r.json()
    out = []
    for it in data.get("value", []):
        out.append({
            "id": it.get("id"),
            "score": it.get("@search.score", None),
            "doc": {f: it.get(f, None) for f in select_fields}
        })
    return out


# ========= 归一化 & 合并 =========
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
    """
    混合评分计算公式说明
    后融合：对两路分数分别做 min-max 归一化，用 alpha 线性加权得到 combined_score，再选前三
    =======================
    combined=α×vec_norm+(1−α)×bm25_norm

    其中：

    vec_norm、bm25_norm 是分别对 top-k 结果的 归一化（min-max）分数

    α（--alpha 参数）是向量权重，例如 0.7 表示语义贡献 70%

    所以：

    vec_raw=0.7227 → vec_norm≈1.0

    bm_raw=66.22 → bm25_norm≈0.6

    combined = 0.7×1.0 + 0.3×0.6 ≈ 0.74
    """
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
    for did, rec in merged.items():
        vecn = rec["vec_score_norm"]
        bmn  = rec["bm25_score_norm"]
        combined = alpha * vecn + (1.0 - alpha) * bmn
        row = {
            "id": did,
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


# ========= 对外主函数 =========
def hybrid_query_top3(
    query_text: str,
    cfg: dict,
    k_vec: int = 3,
    k_bm25: int = 3,
    alpha: float = 0.5,
    select_extra: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    embed_dims = int(cfg.get("embedding_dimensions", 1536))
    embed_model = cfg["embedding_model"]

    embed_client = build_azure_embed_client(cfg)
    qvec = embed_query(embed_client, embed_model, query_text, embed_dims)

    select_fields = list(SELECT_FIELDS)
    if select_extra:
        for f in select_extra:
            if f not in select_fields:
                select_fields.append(f)

    vec_hits = vector_topk_rest(cfg, qvec, k_vec, select_fields)
    bm_hits  = bm25_topk_rest(cfg, query_text, k_bm25, select_fields)
    top3 = merge_and_pick_top(vec_hits, bm_hits, alpha=alpha, top_n=3)

    cleaned = []
    for r in top3:
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
        for f in STRUCT_FIELDS:
            out[f] = r.get(f, None)
        cleaned.append(out)
    return cleaned


def pretty_print(rows: List[Dict[str, Any]]) -> None:
    for i, r in enumerate(rows, 1):
        print("=" * 100)
        print(f"[{i}] combined={r.get('combined_score'):.4f}  vec_raw={r.get('vec_score_raw')}  bm_raw={r.get('bm25_score_raw')}")
        print(f"id={r.get('id')}  chunk_index={r.get('chunk_index')}")
        print(f"filepath={r.get('filepath')}")
        print("-- content (truncated to 600 chars) --")
        c = (r.get("content") or "").strip()
        print(c[:600] + (" ..." if len(c) > 600 else ""))

        print("-- org fields (non-empty) --")
        def _p(key):
            val = r.get(key)
            if val not in (None, [], "", {}):
                print(f"{key}: {val}")
        for key in STRUCT_FIELDS:
            _p(key)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str, help="用户查询文本")
    ap.add_argument("config", type=str, help="config.json 路径")
    ap.add_argument("--alpha", type=float, default=0.5, help="向量归一分数的权重（0~1）")
    ap.add_argument("--kvec", type=int, default=3, help="向量检索条数")
    ap.add_argument("--kbm25", type=int, default=3, help="BM25 检索条数")
    ap.add_argument("--json", action="store_true", help="以 JSON 打印输出")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    rows = hybrid_query_top3(
        args.query, cfg,
        k_vec=args.kvec, k_bm25=args.kbm25, alpha=args.alpha
    )

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        pretty_print(rows)
