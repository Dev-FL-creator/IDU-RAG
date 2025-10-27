# ingest_single.py
import os, sys, json, uuid, re
from typing import List, Dict, Any
from tqdm import tqdm
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import mimetypes


# ---------- PDF utilities ----------
def extract_text_from_document_intelligence(pdf_path, endpoint, key):
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-document", analyze_request=f, content_type="application/pdf")
        result = poller.result()
    return "\n".join([line.content for p in result.pages for line in p.lines])


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
        if chunk: chunks.append(chunk)
        if end >= n: break
        start = max(0, end - overlap)
        if start >= n: break
    return chunks

# ---------- AOAI utilities ----------
def batch_embeddings(client: AzureOpenAI, deployment: str, texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=deployment, input=texts)
    return [item.embedding for item in resp.data]

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

        "members": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "role": {"type": "string"},
                    "affiliation": {"type": "string"}
                }
            }
        },

        "facilities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "usage": {"type": "string"},
                    "location": {"type": "string"}
                }
            }
        },

        "capabilities": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
        "awards": {"type": "array", "items": {"type": "string"}},
        "services": {"type": "array", "items": {"type": "string"}},

        "contacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": ["string", "null"]},
                    "phone": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]}
                }
            }
        },

        "addresses": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"}
    }
}


PROMPT_SYSTEM = (
    "You are a precise information extraction assistant. "
    "Given an organization brochure/manual text, extract a clean JSON object that follows the provided JSON schema. "
    "If a field is missing, use null or an empty list. Do not add fields not in the schema. "
    "Return JSON only, no extra commentary."
)

# 对整份机构文本做结构化信息抽取，产出JSON
def extract_org_json(full_text: str, client: AzureOpenAI, chat_deploy: str) -> Dict[str, Any]:
    # try Responses JSON schema
    try:
        rsp = client.responses.create(
            model=chat_deploy,
            input=[
                {"role":"system","content":PROMPT_SYSTEM},
                {"role":"user","content":"Extract the organization information from the following text as strict JSON.\n\n"+full_text}
            ],
            response_format={"type":"json_schema","json_schema":{"name":"OrgProfile","schema":ORG_SCHEMA,"strict":True}},
            max_output_tokens=2048
        )
        raw = rsp.output[0].content[0].text
        return json.loads(raw)
    except Exception:
        # fallback to chat.completions JSON mode
        rsp = client.chat.completions.create(
            model=chat_deploy,
            messages=[
                {"role":"system","content":PROMPT_SYSTEM},
                {"role":"user","content":"Extract the organization information from the following text as strict JSON.\n\n"+full_text}
            ],
            response_format={"type":"json_object"},
            temperature=0.1
        )
        return json.loads(rsp.choices[0].message.content)
    
# 把抽取结果中的数组对象整理成 Azure Search 索引可直接存的多值字段形式
def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
    # flatten arrays to multi-value fields expected by the index
    members = data.get("members") or []
    facilities = data.get("facilities") or []
    contacts = data.get("contacts") or []

    names  = [c.get("name")  for c in contacts if isinstance(c, dict) and c.get("name")]
    emails = [c.get("email") for c in contacts if isinstance(c, dict) and c.get("email") and re.match(r"[^@]+@[^@]+\.[^@]+", c["email"])]
    phones = [c.get("phone") for c in contacts if isinstance(c, dict) and c.get("phone")]

    flat = {
        "org_name": data.get("org_name"),
        "country":  data.get("country"),
        "address":  data.get("address"),
        "founded_year": data.get("founded_year"),
        "size": data.get("size"),
        "industry": data.get("industry"),
        "is_DU_member": data.get("is_DU_member"),
        "website": data.get("website"),

        "members_name":  [m.get("name")  for m in members if isinstance(m, dict) and m.get("name")],
        "members_title": [m.get("title") for m in members if isinstance(m, dict) and m.get("title")],
        "members_role":  [m.get("role")  for m in members if isinstance(m, dict) and m.get("role")],

        "facilities_name":  [f.get("name")  for f in facilities if isinstance(f, dict) and f.get("name")],
        "facilities_type":  [f.get("type")  for f in facilities if isinstance(f, dict) and f.get("type")],
        "facilities_usage": [f.get("usage") for f in facilities if isinstance(f, dict) and f.get("usage")],

        "capabilities": data.get("capabilities") or [],
        "projects":     data.get("projects") or [],
        "awards":       data.get("awards") or [],
        "services":     data.get("services") or [],
        "contacts_name":  names,
        "contacts_email": emails,
        "contacts_phone": phones,
        "addresses":    data.get("addresses") or [],
        "notes":        data.get("notes")
    }
    return flat

# ---------- main ingest ----------
# 处理一个 PDF，并把所有内容写入同一个索引
def ingest_pdf_single_index(pdf_path: str, cfg: dict):
    source_id = str(uuid.uuid4())
    filename = os.path.basename(pdf_path)

    # clients
    aoai = AzureOpenAI(
        api_key=cfg["openai_api_key"],
        api_version=cfg["openai_api_version"],
        azure_endpoint=cfg["openai_endpoint"],
    )
    embed_deploy = cfg["embedding_model"]
    chat_deploy  = cfg["chat_model"]

    search = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=cfg["index_name"],
        credential=AzureKeyCredential(cfg["search_api_key"])
    )

    # 1) extract full text & structured JSON (once)
    full_text = extract_text_from_document_intelligence(pdf_path, cfg["docint_endpoint"], cfg["docint_key"])
    struct_json = extract_org_json(full_text, aoai, chat_deploy)
    flat_org = flatten_for_index(struct_json)

    # 2) chunk & embed; attach flat_org fields to every chunk doc
    chunks = chunk_text(full_text, max_chunk_size=5000, overlap=200)

    BATCH_EMBED, BATCH_UPLOAD = 16, 64
    docs_batch = []

    for i in tqdm(range(0, len(chunks), BATCH_EMBED), desc="Embedding"):
        sub = chunks[i:i+BATCH_EMBED]
        embs = batch_embeddings(aoai, embed_deploy, sub)

        for j, (ck, emb) in enumerate(zip(sub, embs)):
            idx = i + j
            doc = {
                "id": f"{source_id}-{idx}",
                "source_id": source_id,
                "chunk_index": idx,
                "content": ck,
                "filepath": os.path.abspath(pdf_path),
                "page_from": None,
                "page_to": None,
                "content_vector": emb,
                # merge structured org fields per-chunk
                **flat_org
            }
            docs_batch.append(doc)

            if len(docs_batch) >= BATCH_UPLOAD:
                res = search.merge_or_upload_documents(docs_batch)
                fail = [r for r in res if not r.succeeded]
                if fail:
                    print("[warn] upload failure sample:", fail[0].key, fail[0].error_message)
                docs_batch = []

    if docs_batch:
        res = search.merge_or_upload_documents(docs_batch)
        fail = [r for r in res if not r.succeeded]
        if fail:
            print("[warn] upload failure sample:", fail[0].key, fail[0].error_message)

    print(f"[ok] ingested {len(chunks)} chunks for {filename} | source_id={source_id}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ingest_single.py <pdf_path> <config.json>")
        sys.exit(1)
    pdf, cfgp = sys.argv[1], sys.argv[2]
    with open(cfgp, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    ingest_pdf_single_index(pdf, cfg)
