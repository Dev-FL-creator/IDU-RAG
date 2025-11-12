# routers/pdf_ingest.py
import os, sys, json, uuid, re, glob, math, tempfile, shutil
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient  # 旧客户端稳定
from azure.core.exceptions import ResourceNotFoundError

from openai import OpenAI as OpenAIPlatform, AzureOpenAI

# Import functions from embed_and_ingest_chunks.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from embed_and_ingest_chunks import (
    extract_text_from_pymupdf, 
    extract_org_json,
    flatten_for_index,
    chunk_text,
    batch_embeddings
)

# ---------------------------------------------------------
# Router & progress store
# ---------------------------------------------------------
router = APIRouter(prefix="/api", tags=["pdf-ingest"])
_progress: Dict[str, Dict[str, Any]] = {}

def _set_progress(job_id: str, **kwargs):
    base = _progress.get(job_id, {})
    base.update(kwargs)
    _progress[job_id] = base

# ---------------------------------------------------------
# Config loader
# ---------------------------------------------------------
def load_config() -> dict:
    cfg_path = os.getenv("CONFIG_PATH") or os.path.join(os.path.dirname(__file__), "..", "config.json")
    cfg_path = os.path.abspath(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------
# PDF extraction utils
# ---------------------------------------------------------
def extract_text_from_pymupdf(pdf_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text_content = ""
        for page in doc:
            text_content += page.get_text() + "\n"
        doc.close()
        return text_content
    except ImportError:
        raise RuntimeError("缺少 PyMuPDF，请先安装：pip install PyMuPDF")
    except Exception as e:
        raise RuntimeError(f"PyMuPDF 提取失败: {e}")

def _build_blocks_from_result(result):
    blocks = []
    for p in getattr(result, "paragraphs", []) or []:
        if getattr(p, "content", None):
            page = None
            br = getattr(p, "bounding_regions", None)
            if br:
                try:
                    page = br[0].page_number
                except Exception:
                    page = getattr(br[0], "page_number", None)
            blocks.append({"type": "paragraph", "content": p.content, "page": page})
    for t in getattr(result, "tables", []) or []:
        rows = {}
        for cell in t.cells:
            rows.setdefault(cell.row_index, {})
            rows[cell.row_index][cell.column_index] = (cell.content or "").strip()
        lines = []
        if rows:
            max_r = max(rows.keys())
            max_c = max(max(r.keys()) for r in rows.values()) if rows else -1
            for r in range(max_r + 1):
                row = rows.get(r, {})
                cols = [row.get(c, "") for c in range(max_c + 1)]
                lines.append("\t".join(cols))
        page = None
        br = getattr(t, "bounding_regions", None)
        if br:
            try:
                page = br[0].page_number
            except Exception:
                page = getattr(br[0], "page_number", None)
        if lines:
            blocks.append({"type": "table", "content": "\n".join(lines), "page": page})
    for kv in getattr(result, "key_value_pairs", []) or []:
        k = getattr(getattr(kv, "key", None), "content", None)
        v = getattr(getattr(kv, "value", None), "content", None)
        if k or v:
            page = None
            br = getattr(kv, "bounding_regions", None)
            if br:
                try:
                    page = br[0].page_number
                except Exception:
                    page = getattr(br[0], "page_number", None)
            blocks.append({"type": "kv", "content": f"{k or ''} : {v or ''}".strip(), "page": page})
    return blocks

def extract_text_from_pdf(pdf_path: str, cfg: dict, method: str, fallback: bool):
    """
    返回: (full_text, doc_json, blocks)
    - PyMuPDF: doc_json=None, blocks=None
    - Azure DocInt: 返回结构化三元组
    """
    method = (method or cfg.get("pdf_extraction_method", "pymupdf")).lower()
    backup = "azure_docint" if method == "pymupdf" else "pymupdf"

    def _docint_triplet():
        client = DocumentAnalysisClient(endpoint=cfg["docint_endpoint"], credential=AzureKeyCredential(cfg["docint_key"]))
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-document", document=f)
            result = poller.result()
        blocks = _build_blocks_from_result(result)
        full_text = "\n".join(b["content"] for b in blocks if b["content"]) if blocks else (getattr(result, "content", "") or "")
        doc_json = result.to_dict() if hasattr(result, "to_dict") else None
        return full_text, doc_json, blocks

    try:
        if method == "pymupdf":
            return extract_text_from_pymupdf(pdf_path), None, None
        elif method == "azure_docint":
            return _docint_triplet()
        else:
            raise ValueError(f"不支持的提取方法: {method}")
    except Exception as e:
        if not fallback:
            raise
        # fallback
        if backup == "pymupdf":
            return extract_text_from_pymupdf(pdf_path), None, None
        else:
            return _docint_triplet()

def build_semantic_text(blocks: Optional[List[Dict[str, Any]]], max_chars=12000) -> str:
    if not blocks:
        return ""
    def noise(s: str) -> bool:
        s2 = (s or "").strip().lower()
        return bool(re.match(r"^(page \d+|\d+|contents|table of contents)$", s2))
    paras = [b for b in blocks if b["type"] == "paragraph" and b.get("content") and not noise(b["content"])]
    tables = [b for b in blocks if b["type"] == "table" and b.get("content")]
    kvs    = [b for b in blocks if b["type"] == "kv" and b.get("content")]
    parts = []
    if paras: parts.append("\n".join(p["content"] for p in paras))
    if tables: parts.append("\n".join(t["content"] for t in tables[:10]))
    if kvs: parts.append("\n".join(k["content"] for k in kvs[:100]))
    text = "\n\n".join(parts)
    return text[:max_chars]

def chunk_text(text: str, max_chunk_size=5000, overlap=200) -> List[str]:
    chunks = []
    n = len(text)
    if n == 0: return chunks
    overlap = max(0, min(overlap, max_chunk_size - 1))
    start = 0
    while start < n:
        end = min(start + max_chunk_size, n)
        if end < n:
            bp = text.rfind("\n", start, end)
            if bp == -1 or (end - bp) > 1000:
                bp2 = text.rfind(". ", start, end)
                if bp2 != -1 and (end - bp2) < 1000:
                    bp = bp2
            if bp != -1 and bp > start + 1000:
                end = bp + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n: break
        start = max(0, end - overlap)
    return chunks

def clean_text(text: str) -> str:
    if not text: return text
    t = text
    t = re.sub(r":selected:", "", t, flags=re.I)
    t = re.sub(r"(?i)\b(ACCESS|KARRIERE|NEWS|NEUIGKEITEN|ENGLISH|DEUTSCH|KONTAKT|ÜBER\s+UNS|FORSCHUNG\s*&\s*ENTWICKLUNG|DIENSTLEISTUNGEN\s*&\s*PRODUKTE|PRODUKTE|IMPRESSUM)\b", "", t)
    t = re.sub(r"[-•=]{2,}", "", t)
    t = re.sub(r"([A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+)\s*", r"\1 ", t)
    t = re.sub(r"Temperature\s*\(C\).*?(?=\n[A-ZÄÖÜ]|$)", "", t, flags=re.S)
    t = re.sub(r"\n{2,}", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()

# ---------------------------------------------------------
# Clients & embeddings
# ---------------------------------------------------------
def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
    return AzureOpenAI(
        api_key=cfg["openai_api_key"],
        api_version=cfg["openai_api_version"],
        azure_endpoint=cfg["openai_endpoint"],
    )

def build_deepseek_chat_client(cfg: dict) -> OpenAIPlatform:
    return OpenAIPlatform(
        api_key=cfg["deepseek_api_key"],
        base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com")
    )

def _pad_or_truncate(vecs: List[List[float]], target_dim: int) -> List[List[float]]:
    fixed = []
    for v in vecs:
        if len(v) == target_dim:
            fixed.append(v)
        elif len(v) > target_dim:
            fixed.append(v[:target_dim])
        else:
            fixed.append(v + [0.0] * (target_dim - len(v)))
    return fixed

def batch_embeddings(azure_embed_client: AzureOpenAI, model: str, texts: List[str], target_dim: int) -> List[List[float]]:
    resp = azure_embed_client.embeddings.create(model=model, input=texts)
    vecs = [item.embedding for item in resp.data]
    return _pad_or_truncate(vecs, target_dim)

# ---------------------------------------------------------
# JSON extraction via DeepSeek
# ---------------------------------------------------------
ORG_SCHEMA = {
    "type": "object",
    "properties": {
        "org_name": {"type": "string"},
        "country": {"type": "string"},
        "address": {"type": "string"},
        "founded_year": {"type": ["integer", "null"]},
        "size": {"type": "string"},
        "industry": {"type": "string"},
        "is_DU_member": {"type": ["boolean", "null"]},
        "website": {"type": ["string", "null"]},
        "contacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": ["string", "null"]},
                    "phone": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                    "address": {"type": ["string", "null"]},
                },
            },
        },
        "members": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": ["string", "null"]},
                    "role": {"type": ["string", "null"]},
                },
            },
        },
        "facilities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": ["string", "null"]},
                    "usage": {"type": ["string", "null"]},
                },
            },
        },
        "capabilities": {"type": "array","items": {"type": "string"}},
        "projects": {"type": "array","items": {"type": "string"}},
        "awards": {"type": "array","items": {"type": "string"}},
        "services": {"type": "array","items": {"type": "string"}},
        "notes": {"type": "string"},
    },
}

PROMPT_SYSTEM = (
    "You are a precise information extraction assistant. "
    "Given an organization brochure/manual text, extract a comprehensive JSON object that follows the provided JSON schema. "
    "If a field is missing, use null or []. Return JSON only."
)

def ensure_schema_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    schema_defaults = {
        "org_name": None, "country": None, "address": None, "founded_year": None,
        "size": None, "industry": None, "is_DU_member": None, "website": None,
        "contacts": [], "members": [], "facilities": [],
        "capabilities": [], "projects": [], "awards": [], "services": [], "notes": None
    }
    result = {}
    for field, default_value in schema_defaults.items():
        if field in data and data[field] is not None:
            value = data[field]
            if field in ["contacts", "members", "facilities"]:
                result[field] = [item for item in value] if isinstance(value, list) else []
            elif field in ["capabilities", "projects", "awards", "services"]:
                if isinstance(value, list):
                    result[field] = [str(item) for item in value if item]
                elif isinstance(value, str) and value.strip():
                    result[field] = [value.strip()]
                else:
                    result[field] = []
            elif field == "founded_year":
                if isinstance(value, int):
                    result[field] = value
                elif isinstance(value, str) and value.isdigit():
                    result[field] = int(value)
                else:
                    result[field] = None
            elif field == "is_DU_member":
                if isinstance(value, bool):
                    result[field] = value
                elif isinstance(value, str):
                    result[field] = value.lower() in ["true", "yes", "1", "是"]
                else:
                    result[field] = None
            else:
                result[field] = str(value).strip() if value else None
        else:
            result[field] = default_value
    return result

def get_empty_schema_result() -> Dict[str, Any]:
    return {
        "org_name": None, "country": None, "address": None, "founded_year": None,
        "size": None, "industry": None, "is_DU_member": None, "website": None,
        "contacts": [], "members": [], "facilities": [],
        "capabilities": [], "projects": [], "awards": [], "services": [], "notes": None
    }

def extract_org_json(full_text: str, deepseek_client: OpenAIPlatform, chat_model: str) -> Dict[str, Any]:
    try:
        schema_str = json.dumps(ORG_SCHEMA, indent=2, ensure_ascii=False)
        enhanced_prompt = f"""{PROMPT_SYSTEM}

Follow this JSON Schema strictly:

{schema_str}

Rules:
- Only extract facts explicitly present
- Use null for missing scalars; [] for missing arrays
- Field names must match schema exactly
- Return valid JSON only
"""
        rsp = deepseek_client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": f"Extract organization information from this text:\n\n{full_text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )
        raw = rsp.choices[0].message.content
        data = json.loads(raw)
        return ensure_schema_compliance(data)
    except Exception:
        return get_empty_schema_result()

def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
    contacts = data.get("contacts") or []
    members  = data.get("members") or []
    facilities = data.get("facilities") or []

    contacts_name  = [c.get("name") for c in contacts if isinstance(c, dict) and c.get("name")]
    contacts_email = [c.get("email") for c in contacts if isinstance(c, dict) and c.get("email")]
    contacts_phone = [c.get("phone") for c in contacts if isinstance(c, dict) and c.get("phone")]

    members_name = [m.get("name") for m in members if isinstance(m, dict) and m.get("name")]
    members_title = [m.get("title") for m in members if isinstance(m, dict) and m.get("title")]
    members_role = [m.get("role") for m in members if isinstance(m, dict) and m.get("role")]

    facilities_name = [f.get("name") for f in facilities if isinstance(f, dict) and f.get("name")]
    facilities_type = [f.get("type") for f in facilities if isinstance(f, dict) and f.get("type")]
    facilities_usage = [f.get("usage") for f in facilities if isinstance(f, dict) and f.get("usage")]

    capabilities = data.get("capabilities") or []
    if isinstance(capabilities, str): capabilities = [capabilities]
    elif not isinstance(capabilities, list): capabilities = []

    projects = data.get("projects") or []
    if isinstance(projects, str): projects = [projects]
    elif not isinstance(projects, list): projects = []

    awards = data.get("awards") or []
    if isinstance(awards, str): awards = [awards]
    elif not isinstance(awards, list): awards = []

    services = data.get("services") or []
    if isinstance(services, str): services = [services]
    elif not isinstance(services, list): services = []

    addresses = []
    if data.get("address"): addresses.append(data.get("address"))
    if data.get("addresses"):
        if isinstance(data.get("addresses"), list): addresses.extend(data.get("addresses"))
        else: addresses.append(str(data.get("addresses")))
    for c in contacts:
        if isinstance(c, dict) and c.get("address"): addresses.append(c.get("address"))

    return {
        "org_name": data.get("org_name"),
        "country": data.get("country"),
        "address": data.get("address"),
        "founded_year": data.get("founded_year"),
        "size": data.get("size"),
        "industry": data.get("industry"),
        "is_DU_member": data.get("is_DU_member"),
        "website": data.get("website"),

        "members_name": members_name,
        "members_title": members_title,
        "members_role": members_role,

        "facilities_name": facilities_name,
        "facilities_type": facilities_type,
        "facilities_usage": facilities_usage,

        "capabilities": capabilities,
        "projects": projects,
        "awards": awards,
        "services": services,

        "contacts_name": contacts_name,
        "contacts_email": contacts_email,
        "contacts_phone": contacts_phone,

        "addresses": addresses,
        "notes": data.get("notes"),

        "page_from": None,
        "page_to": None,
    }

# ---------------------------------------------------------
# Request model (form-friendly defaults)
# ---------------------------------------------------------
class IngestOptions(BaseModel):
    index_name: Optional[str] = None
    embedding_model: Optional[str] = None   # Azure embedding 部署名
    embedding_dimensions: Optional[int] = 1536
    chat_model: Optional[str] = "deepseek-chat"  # 为空则跳过 JSON 抽取
    pdf_extraction_method: str = Field(default="pymupdf", description="pymupdf | azure_docint")
    pdf_extraction_fallback: bool = True
    batch_upload_size: int = 64
    chunk_size: Optional[int] = None        # None=auto
    chunk_overlap: Optional[int] = None     # None=auto
    write_action: str = Field(default="mergeOrUpload")  # upload|mergeOrUpload|merge|delete

# ---------------------------------------------------------
# Background job
# ---------------------------------------------------------
def _ingest_single_pdf(
    pdf_path: str,
    cfg: dict,
    options: IngestOptions,
    search: SearchClient,
    azure_embed_client: AzureOpenAI,
    deepseek_client: Optional[OpenAIPlatform],
):
    source_id = str(uuid.uuid4())
    filename = os.path.basename(pdf_path)

    # 1) extract
    full_text, doc_json, blocks = extract_text_from_pdf(
        pdf_path,
        cfg,
        method=options.pdf_extraction_method,
        fallback=options.pdf_extraction_fallback,
    )
    full_text = clean_text(full_text)

    # 2) JSON extraction
    struct_json = {}
    if options.chat_model and deepseek_client is not None:
        semantic_text = build_semantic_text(blocks) if blocks else full_text
        text_for_llm = semantic_text if semantic_text else full_text
        struct_json = extract_org_json(text_for_llm, deepseek_client, options.chat_model) or {}
    flat_org = flatten_for_index(struct_json) if struct_json else {}

    # 3) chunking
    text_len = len(full_text)
    if options.chunk_size is not None:
        chunk_size = max(200, int(options.chunk_size))
        overlap = max(0, int(options.chunk_overlap or 0))
    else:
        if text_len <= 3000:
            chunk_size = max(500, text_len // 3)
            overlap = min(100, chunk_size // 10)
        else:
            chunk_size = 5000
            overlap = 200
    chunks = chunk_text(full_text, max_chunk_size=chunk_size, overlap=overlap)

    # 4) embeddings + upload
    docs_batch = []
    embed_dims = int(options.embedding_dimensions or cfg.get("embedding_dimensions", 1536))
    embed_model = options.embedding_model or cfg["embedding_model"]
    for i in range(0, len(chunks), 16):
        sub = chunks[i:i+16]
        embs = batch_embeddings(azure_embed_client, embed_model, sub, embed_dims)
        for j, (ck, emb) in enumerate(zip(sub, embs)):
            idx = i + j
            doc = {
                "id": f"{source_id}-{idx}",
                "source_id": source_id,
                "chunk_index": idx,
                "content": ck,
                "filepath": os.path.abspath(pdf_path),
                "content_vector": emb,
                **flat_org,
            }
            docs_batch.append(doc)
        if len(docs_batch) >= options.batch_upload_size:
            search.merge_or_upload_documents(docs_batch)
            docs_batch = []
    if docs_batch:
        search.merge_or_upload_documents(docs_batch)

    return {
        "filename": filename,
        "source_id": source_id,
        "chunks": len(chunks),
        "chunk_size": chunk_size,
        "overlap": overlap,
        "text_len": text_len,
    }

def _process_pdfs_job(job_id: str, tempdir: str, filenames: List[str], options: IngestOptions):
    cfg = load_config()
    index_name = options.index_name or cfg["index_name"]

    search = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=index_name,
        credential=AzureKeyCredential(cfg["search_api_key"]),
    )
    azure_embed_client = build_azure_embed_client(cfg)
    deepseek_client = None
    if options.chat_model:
        try:
            deepseek_client = build_deepseek_chat_client(cfg)
        except Exception:
            deepseek_client = None

    total = len(filenames)
    results = []
    _set_progress(job_id, status="running", current=0, total=total, files=[], errors=[])

    for i, name in enumerate(filenames, 1):
        pdf_path = os.path.join(tempdir, name)
        _set_progress(job_id, status="extracting", current_file=name, current=i-1, total=total)
        try:
            res = _ingest_single_pdf(pdf_path, cfg, options, search, azure_embed_client, deepseek_client)
            results.append(res)
            files = _progress[job_id].get("files", [])
            files.append({"file": name, "ok": True, "source_id": res["source_id"], "chunks": res["chunks"]})
            _set_progress(job_id, status="indexing", current=i, total=total, files=files)
        except Exception as e:
            files = _progress[job_id].get("files", [])
            files.append({"file": name, "ok": False, "error": str(e)})
            errs = _progress[job_id].get("errors", [])
            errs.append(f"{name}: {e}")
            _set_progress(job_id, status="error_partial", current=i, total=total, files=files, errors=errs)

    _set_progress(job_id, status="done", summary=results)

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------
@router.post("/upload_pdfs")
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="One or more PDF files"),
    index_name: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    embedding_dimensions: Optional[int] = Form(1536),
    chat_model: Optional[str] = Form("deepseek-chat"),
    pdf_extraction_method: str = Form("pymupdf"),
    pdf_extraction_fallback: bool = Form(True),
    batch_upload_size: int = Form(64),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    write_action: str = Form("mergeOrUpload"),
):
    # save to tempdir
    tmpdir = tempfile.mkdtemp(prefix="pdf_upl_")
    saved: List[str] = []
    try:
        for f in files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in (".pdf",):
                continue
            dest = os.path.join(tmpdir, f.filename)
            with open(dest, "wb") as out:
                out.write(await f.read())
            saved.append(f.filename)
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to save uploads: {e}")

    if not saved:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="No valid PDF files were uploaded.")

    job_id = str(uuid.uuid4())
    _set_progress(job_id, status="queued", current=0, total=len(saved))

    options = IngestOptions(
        index_name=index_name,
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        chat_model=chat_model,
        pdf_extraction_method=pdf_extraction_method,
        pdf_extraction_fallback=pdf_extraction_fallback,
        batch_upload_size=batch_upload_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        write_action=write_action,
    )

    # kick off background ingestion
    background_tasks.add_task(_process_pdfs_job, job_id, tmpdir, saved, options)

    return {"ok": True, "job_id": job_id, "files": saved}

@router.get("/progress/{job_id}")
def get_progress(job_id: str):
    return _progress.get(job_id, {"status": "unknown", "job_id": job_id})

@router.get("/health")
def health():
    try:
        cfg = load_config()
        return {"ok": True, "has_config": True, "search_service": cfg.get("search_service_name")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---------------------------------------------------------
# PDF Preview Extraction (without indexing)
# ---------------------------------------------------------
@router.post("/extract_pdf_preview")
async def extract_pdf_preview(
    files: List[UploadFile] = File(..., description="One or more PDF files for preview"),
    chat_model: Optional[str] = Form("deepseek-chat"),
    pdf_extraction_method: str = Form("pymupdf"),
    pdf_extraction_fallback: bool = Form(True),
):
    """Extract and return structured information from PDFs without indexing"""
    tmpdir = tempfile.mkdtemp(prefix="pdf_preview_")
    saved_files: List[str] = []
    extracted_data = []
    
    try:
        # Save uploaded files
        for f in files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in (".pdf",):
                continue
            dest = os.path.join(tmpdir, f.filename)
            with open(dest, "wb") as out:
                out.write(await f.read())
            saved_files.append(dest)
        
        if not saved_files:
            raise HTTPException(status_code=400, detail="No valid PDF files were uploaded.")
        
        cfg = load_config()
        
        # Process each PDF
        for pdf_path in saved_files:
            filename = os.path.basename(pdf_path)
            
            # Extract text from PDF
            text_content = ""
            print(f"Extracting text from {filename} using method: {pdf_extraction_method}")
            
            if pdf_extraction_method == "pymupdf":
                text_content = extract_text_from_pymupdf(pdf_path)
                print(f"PyMuPDF extracted {len(text_content)} characters from {filename}")
            else:
                # Use the comprehensive extract_text_from_pdf function that handles Azure DI
                # This function returns (full_text, doc_json, blocks)
                result = extract_text_from_pdf(pdf_path, cfg, pdf_extraction_method, pdf_extraction_fallback)
                if isinstance(result, tuple):
                    text_content = result[0]  # Take only the text content
                else:
                    text_content = result
                print(f"extract_text_from_pdf extracted {len(text_content)} characters from {filename}")
            
            # Apply fallback if needed
            if not text_content or len(text_content.strip()) < 50:
                print(f"Text too short ({len(text_content)} chars), trying fallback...")
                if pdf_extraction_fallback:
                    if pdf_extraction_method == "pymupdf":
                        # Try Azure Document Intelligence as fallback
                        print("Trying Azure Document Intelligence as fallback...")
                        result = extract_text_from_pdf(pdf_path, cfg, "azure_docint", False)
                        if isinstance(result, tuple):
                            text_content = result[0]
                        else:
                            text_content = result
                        print(f"Azure DI fallback extracted {len(text_content)} characters")
                    else:
                        # Try PyMuPDF as fallback
                        print("Trying PyMuPDF as fallback...")
                        text_content = extract_text_from_pymupdf(pdf_path)
                        print(f"PyMuPDF fallback extracted {len(text_content)} characters")
            
            if text_content and len(text_content.strip()) >= 50:
                # Use DeepSeek to extract structured information
                deepseek_client = OpenAIPlatform(
                    api_key=cfg.get("deepseek_api_key"),
                    base_url="https://api.deepseek.com"
                )
                structured_info = extract_org_json(text_content, deepseek_client, chat_model)
                
                extracted_data.append({
                    "filename": filename,
                    "text_length": len(text_content),
                    "structured_info": structured_info,
                    "raw_text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content,
                    "raw_text": text_content  # Store full text for chunking later
                })
            else:
                # More detailed error information
                text_len = len(text_content) if text_content else 0
                if text_len == 0:
                    error_msg = "No text could be extracted from PDF. This might be a scanned document or image-only PDF."
                elif text_len < 50:
                    error_msg = f"Extracted text too short ({text_len} characters). PDF might be mostly images or have formatting issues."
                else:
                    error_msg = "Could not extract sufficient text from PDF"
                
                extracted_data.append({
                    "filename": filename,
                    "error": error_msg,
                    "text_length": text_len,
                    "raw_text_preview": text_content[:200] if text_content else "No text extracted"
                })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        # Clean up temp files
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    return {
        "ok": True,
        "extracted_data": extracted_data,
        "total_files": len(saved_files)
    }

# ---------------------------------------------------------
# Confirm and Index Extracted Data
# ---------------------------------------------------------
class ConfirmIndexRequest(BaseModel):
    extracted_data: List[Dict[str, Any]]
    index_name: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = 1536
    batch_upload_size: int = 64
    write_action: str = "mergeOrUpload"

@router.post("/confirm_and_index")
async def confirm_and_index(
    background_tasks: BackgroundTasks,
    request: ConfirmIndexRequest
):
    """Index the confirmed extracted data to Azure Search"""
    try:
        cfg = load_config()
        job_id = str(uuid.uuid4())
        
        # Set progress
        total_items = len(request.extracted_data)
        _set_progress(job_id, status="processing", current=0, total=total_items)
        
        # Create options
        options = IngestOptions(
            index_name=request.index_name,
            embedding_model=request.embedding_model,
            embedding_dimensions=request.embedding_dimensions,
            batch_upload_size=request.batch_upload_size,
            write_action=request.write_action
        )
        
        # Process in background
        background_tasks.add_task(_process_confirmed_data, job_id, request.extracted_data, options, cfg)
        
        return {
            "ok": True,
            "job_id": job_id,
            "message": f"Started indexing {total_items} extracted items"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

# ---------------------------------------------------------
# Background task for confirmed data
# ---------------------------------------------------------
async def _process_confirmed_data(job_id: str, extracted_data: List[Dict[str, Any]], options: IngestOptions, cfg: dict):
    """Process confirmed extracted data and index to Azure Search"""
    try:
        _set_progress(job_id, status="processing", message="Preparing to index confirmed data")
        
        # Process each PDF and create chunks
        all_docs = []
        for i, data in enumerate(extracted_data):
            if "structured_info" not in data or "error" in data:
                continue
                
            structured_info = data["structured_info"]
            filename = data["filename"]
            raw_text = data.get("raw_text", "")  # Get the full extracted text
            
            # Generate a unique source_id for this PDF
            source_id = str(uuid.uuid4())
            
            # Clean filename for file path
            clean_filename = re.sub(r'[^a-zA-Z0-9_\-=.]', '_', filename)
            
            # Flatten organization info for indexing (following embed_and_ingest_chunks.py pattern)
            flat_org = flatten_for_index(structured_info)
            
            # Chunk the full text (following embed_and_ingest_chunks.py logic)
            text_len = len(raw_text)
            if text_len <= 3000:
                chunk_size = max(500, text_len // 3)
                overlap = min(100, chunk_size // 10)
            else:
                chunk_size = 5000
                overlap = 200
            
            chunks = chunk_text(raw_text, max_chunk_size=chunk_size, overlap=overlap)
            
            # Create document for each chunk
            for chunk_idx, chunk_content in enumerate(chunks):
                doc_id = f"{source_id}-{chunk_idx}"
                doc = {
                    "id": doc_id,
                    "source_id": source_id,
                    "chunk_index": chunk_idx,
                    "content": chunk_content,
                    "filepath": clean_filename,
                    **flat_org  # Include all flattened organization fields
                }
                all_docs.append(doc)
            
            _set_progress(job_id, current=i+1, message=f"Processed {filename}: {len(chunks)} chunks")
        
        if not all_docs:
            _set_progress(job_id, status="completed", message="No valid data to index")
            return
        
        # Index to Azure Search
        _set_progress(job_id, message="Indexing to Azure Search...")
        
        # Setup clients and parameters
        index_name = options.index_name or cfg.get("index_name", "pdf-knowledge-base-access-all")
        embedding_model = options.embedding_model or cfg.get("embedding_model", "text-embedding-3-small")
        embedding_dimensions = options.embedding_dimensions or cfg.get("embedding_dimensions", 1536)
        batch_size = options.batch_upload_size or 64
        
        # Create Azure OpenAI client for embeddings
        azure_embed_client = AzureOpenAI(
            api_key=cfg["openai_api_key"],
            api_version=cfg["openai_api_version"],
            azure_endpoint=cfg["openai_endpoint"]
        )
        
        # Create Search client
        search_client = SearchClient(
            endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
            index_name=index_name,
            credential=AzureKeyCredential(cfg["search_api_key"])
        )
        
        # Generate embeddings in batches and upload (following embed_and_ingest_chunks.py pattern)
        docs_batch = []
        for i in range(0, len(all_docs), 16):  # Process 16 docs at a time for embedding
            sub_docs = all_docs[i:i+16]
            texts = [doc["content"] for doc in sub_docs]
            
            # Generate embeddings for this batch
            embeddings = batch_embeddings(azure_embed_client, embedding_model, texts, embedding_dimensions)
            
            # Add embeddings to documents
            for doc, embedding in zip(sub_docs, embeddings):
                doc["content_vector"] = embedding
                docs_batch.append(doc)
            
            # Upload when batch is full
            if len(docs_batch) >= batch_size:
                search_client.merge_or_upload_documents(docs_batch)
                _set_progress(job_id, message=f"Uploaded {len(docs_batch)} documents")
                docs_batch = []
        
        # Upload remaining documents
        if docs_batch:
            search_client.merge_or_upload_documents(docs_batch)
            _set_progress(job_id, message=f"Uploaded final {len(docs_batch)} documents")
        
        _set_progress(job_id, status="completed", current=len(all_docs), message=f"Successfully indexed {len(all_docs)} items")
        
    except Exception as e:
        _set_progress(job_id, status="error", message=f"Error: {str(e)}")
        print(f"Error in _process_confirmed_data: {e}")
        import traceback
        traceback.print_exc()
