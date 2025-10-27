# ingest_single.py —— 混合模式：Embedding 用 Azure（已部署），Chat 用 DeepSeek（OpenAI 兼容）
import os, sys, json, uuid, re, mimetypes
from typing import List, Dict, Any
from tqdm import tqdm

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.exceptions import ResourceNotFoundError

# ✅ DeepSeek 走 OpenAI 兼容客户端；Azure Embedding 走 AzureOpenAI
from openai import OpenAI as OpenAIPlatform, AzureOpenAI


# ========== PDF utilities ==========
def extract_text_from_document_intelligence(pdf_path, endpoint, key):
    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-document", document=f)
        result = poller.result()

    if getattr(result, "paragraphs", None):
        lines = [p.content for p in result.paragraphs if p.content]
        return "\n".join(lines)
    if getattr(result, "content", None):
        return result.content

    # 兜底
    text_blocks = []
    for table in getattr(result, "tables", []) or []:
        for cell in table.cells:
            if cell.content:
                text_blocks.append(cell.content)
    return "\n".join(text_blocks)


def chunk_text(text: str, max_chunk_size=5000, overlap=200) -> List[str]:
    chunks = []
    n = len(text)
    if n == 0:
        return chunks
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
        if end >= n:
            break
        start = max(0, end - overlap)
        if start >= n:
            break
    return chunks


# ========== Clients ==========
def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
    """
    Azure Embedding 客户端（需要你已在 Azure 上部署 embedding 模型）。
    cfg 需包含：openai_api_key, openai_api_version, openai_endpoint
    """
    return AzureOpenAI(
        api_key=cfg["openai_api_key"],
        api_version=cfg["openai_api_version"],
        azure_endpoint=cfg["openai_endpoint"],
    )

def build_deepseek_chat_client(cfg: dict) -> OpenAIPlatform:
    """
    DeepSeek Chat 客户端（OpenAI 兼容）。
    cfg 需包含：deepseek_api_key；可选 deepseek_base_url (默认 https://api.deepseek.com)
    """
    return OpenAIPlatform(
        api_key=cfg["deepseek_api_key"],
        base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com")
    )


# ========== Embeddings ==========
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
    """
    - 使用 Azure 部署好的 embedding （model=部署名）
    - 失败时回退本地 sentence-transformers（需已安装）
    """
    try:
        resp = azure_embed_client.embeddings.create(model=model, input=texts)
        vecs = [item.embedding for item in resp.data]
        return _pad_or_truncate(vecs, target_dim)
    except Exception as e:
        print("[warn] Azure embedding 失败，回退本地 sentence-transformers：", e)
        try:
            from sentence_transformers import SentenceTransformer
            st = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")  # 384维
            vecs = st.encode(texts, normalize_embeddings=True).tolist()
            return _pad_or_truncate(vecs, target_dim)
        except Exception as ee:
            raise RuntimeError("本地 embedding 失败，请安装 sentence-transformers 或检查 Azure 部署与密钥") from ee


# ========== JSON 抽取（DeepSeek Chat）==========
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
                },
            },
        },
        "notes": {"type": "string"},
    },
}

PROMPT_SYSTEM = (
    "You are a precise information extraction assistant. "
    "Given an organization brochure/manual text, extract a clean JSON object that follows the provided JSON schema. "
    "If a field is missing, use null or an empty list. Do not add fields not in the schema. "
    "Return JSON only, no extra commentary."
)

def extract_org_json(full_text: str, deepseek_client: OpenAIPlatform, chat_model: str) -> Dict[str, Any]:
    try:
        rsp = deepseek_client.responses.create(
            model=chat_model,  # e.g., "deepseek-chat"
            input=[
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": "Extract the organization information from the following text as strict JSON.\n\n" + full_text},
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "OrgProfile", "schema": ORG_SCHEMA, "strict": True}},
            max_output_tokens=2048,
        )
        raw = rsp.output[0].content[0].text
        return json.loads(raw)
    except Exception:
        # fallback：chat.completions
        rsp = deepseek_client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": "Extract the organization information from the following text as strict JSON.\n\n" + full_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(rsp.choices[0].message.content)


def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
    contacts = data.get("contacts") or []
    names = [c.get("name") for c in contacts if c.get("name")]
    emails = [c.get("email") for c in contacts if c.get("email")]
    phones = [c.get("phone") for c in contacts if c.get("phone")]

    return {
        "org_name": data.get("org_name"),
        "country": data.get("country"),
        "address": data.get("address"),
        "founded_year": data.get("founded_year"),
        "size": data.get("size"),
        "industry": data.get("industry"),
        "is_DU_member": data.get("is_DU_member"),
        "website": data.get("website"),
        "contacts_name": names,
        "contacts_email": emails,
        "contacts_phone": phones,
        "notes": data.get("notes"),
    }


# ========== main ingest ==========
def ingest_pdf_single_index(pdf_path: str, cfg: dict):
    source_id = str(uuid.uuid4())
    filename = os.path.basename(pdf_path)

    # Embedding 用 Azure（部署名）
    azure_embed_client = build_azure_embed_client(cfg)

    # Chat 用 DeepSeek
    deepseek_client = build_deepseek_chat_client(cfg)

    embed_model = cfg["embedding_model"]                 # ⚠️ 这里是 Azure“部署名”
    chat_model = cfg.get("chat_model", "deepseek-chat")  # DeepSeek 模型名
    embed_dims = int(cfg.get("embedding_dimensions", 1536))

    # Azure Search
    search = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=cfg["index_name"],
        credential=AzureKeyCredential(cfg["search_api_key"]),
    )

    # 1) PDF 提取文字
    full_text = extract_text_from_document_intelligence(pdf_path, cfg["docint_endpoint"], cfg["docint_key"])

    # 2) JSON 抽取（DeepSeek）
    if chat_model:
        try:
            struct_json = extract_org_json(full_text, deepseek_client, chat_model)
        except Exception as e:
            print(f"[warn] JSON 抽取失败：{e}")
            struct_json = {}
    else:
        struct_json = {}

    flat_org = flatten_for_index(struct_json) if struct_json else {}

    # 3) chunk + embedding(Azure) + 上传
    chunks = chunk_text(full_text)
    docs_batch = []
    for i in tqdm(range(0, len(chunks), 16), desc="Embedding"):
        sub = chunks[i:i + 16]
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
        # 批量上传
        if len(docs_batch) >= 64:
            search.merge_or_upload_documents(docs_batch)
            docs_batch = []

    if docs_batch:
        search.merge_or_upload_documents(docs_batch)

    print(f"[ok] Ingested {len(chunks)} chunks for {filename} | source_id={source_id}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ingest_single.py <pdf_path> <config.json>")
        sys.exit(1)
    pdf, cfgp = sys.argv[1], sys.argv[2]
    with open(cfgp, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    ingest_pdf_single_index(pdf, cfg)
