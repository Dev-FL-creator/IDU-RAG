# 提取pdf文本，组织语料为结构化格式，使用 DeepSeek 进行 JSON 抽取
#无debug 不输出调试文件

import os, sys, json, uuid, re, mimetypes, glob
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.ai.documentintelligence import DocumentIntelligenceClient  # 保留导入（不使用）
from azure.ai.formrecognizer import DocumentAnalysisClient            # 使用旧客户端
from azure.core.exceptions import ResourceNotFoundError

# DeepSeek 走 OpenAI 兼容客户端；Azure Embedding 走 AzureOpenAI
from openai import OpenAI as OpenAIPlatform, AzureOpenAI


# ========== PDF utilities ==========
def extract_text_from_pymupdf(pdf_path: str) -> str:
    """使用PyMuPDF提取PDF文本"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        text_content = ""
        total_pages = len(doc)
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            text_content += page.get_text() + "\n"
        doc.close()
        print(f"[info] PyMuPDF成功提取{len(text_content)}字符（{total_pages}页）")
        return text_content
    except ImportError:
        raise ImportError("PyMuPDF (fitz) 未安装，请运行: pip install PyMuPDF")
    except Exception as e:
        raise RuntimeError(f"PyMuPDF提取失败：{e}")


def _build_blocks_from_result(result):
    """从 Form Recognizer/DI 的 result 构建轻量 blocks 列表"""
    blocks = []

    # 段落
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

    # 表格 -> TSV
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
        if lines:
            page = None
            br = getattr(t, "bounding_regions", None)
            if br:
                try:
                    page = br[0].page_number
                except Exception:
                    page = getattr(br[0], "page_number", None)
            blocks.append({"type": "table", "content": "\n".join(lines), "page": page})

    # 键值对
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


def extract_text_from_document_intelligence(pdf_path, endpoint, key):
    """使用Azure Document Intelligence提取文本（旧 SDK 客户端，稳定）"""
    try:
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-document", document=f)
            result = poller.result()

        text_content = ""
        if getattr(result, "paragraphs", None):
            lines = [p.content for p in result.paragraphs if p.content]
            text_content = "\n".join(lines)
        elif getattr(result, "content", None):
            text_content = result.content
        else:
            text_blocks = []
            for table in getattr(result, "tables", []) or []:
                for cell in table.cells:
                    if cell.content:
                        text_blocks.append(cell.content)
            text_content = "\n".join(text_blocks)

        azure_pages = len(result.pages) if hasattr(result, 'pages') and result.pages else 0
        print(f"[info] Azure Document Intelligence成功提取{len(text_content)}字符（{azure_pages}页）")
        return text_content
    except Exception as e:
        raise RuntimeError(f"Azure Document Intelligence提取失败：{e}")


def extract_text_from_pdf(pdf_path: str, cfg: dict):
    """
    返回: (full_text, doc_json, blocks)
    - 当使用 PyMuPDF 时：doc_json=None, blocks=None
    - 当使用 Azure DocInt 时：返回结构化后的三元组
    """
    method = cfg.get("pdf_extraction_method", "pymupdf").lower()
    fallback = cfg.get("pdf_extraction_fallback", True)
    primary = method
    backup = "azure_docint" if method == "pymupdf" else "pymupdf"

    print(f"[info] 使用PDF提取方法: {primary} (备选: {backup if fallback else '无'})")

    def _docint_triplet():
        client = DocumentAnalysisClient(endpoint=cfg["docint_endpoint"], credential=AzureKeyCredential(cfg["docint_key"]))
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-document", document=f)
            result = poller.result()
        blocks = _build_blocks_from_result(result)
        full_text = "\n".join(b["content"] for b in blocks if b["content"]) if blocks else (getattr(result, "content", "") or "")
        doc_json = result.to_dict() if hasattr(result, "to_dict") else None
        pages = len(result.pages) if getattr(result, "pages", None) else 0
        print(f"[info] DocInt(prebuilt-document) 提取: {len(full_text)} 字符（{pages}页，块={len(blocks)}）")
        return full_text, doc_json, blocks

    try:
        if primary == "pymupdf":
            text = extract_text_from_pymupdf(pdf_path)
            return text, None, None
        elif primary == "azure_docint":
            return _docint_triplet()
        else:
            raise ValueError(f"不支持的PDF提取方法: {primary}")
    except Exception as e:
        print(f"[warn] {primary} 提取失败：{e}")
        if not fallback:
            raise e
        print(f"[info] 切换到备选方法: {backup}")
        try:
            if backup == "pymupdf":
                text = extract_text_from_pymupdf(pdf_path)
                return text, None, None
            elif backup == "azure_docint":
                return _docint_triplet()
        except Exception as ee:
            raise RuntimeError(f"所有PDF提取方法都失败。主要方法({primary})：{e}，备选方法({backup})：{ee}")
        raise e  # 如果没有备选方法成功，抛出原始错误


def build_semantic_text(blocks: Optional[List[Dict[str, Any]]], max_chars=12000) -> str:
    """将段落/表格/KV组织成较干净的抽取语料"""
    if not blocks:
        return ""
    def noise(s: str) -> bool:
        s2 = (s or "").strip().lower()
        return bool(re.match(r"^(page \d+|\d+|contents|table of contents)$", s2))
    paras = [b for b in blocks if b["type"] == "paragraph" and b.get("content") and not noise(b["content"])]
    tables = [b for b in blocks if b["type"] == "table" and b.get("content")]
    kvs    = [b for b in blocks if b["type"] == "kv" and b.get("content")]

    parts = []
    if paras:
        parts.append("\n".join(p["content"] for p in paras))
    if tables:
        parts.append("\n".join(t["content"] for t in tables[:10]))
    if kvs:
        parts.append("\n".join(k["content"] for k in kvs[:100]))
    text = "\n\n".join(parts)
    return text[:max_chars]


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


def clean_text(text: str) -> str:
    """清理提取文本中的常见网页/版面噪音"""
    if not text:
        return text
    t = text

    # 1. 去掉 :selected:、:: 等标记
    t = re.sub(r":selected:", "", t)
    t = re.sub(r"\s+:\s+", ": ", t)

    # 2. 去掉多余符号与温度、图表残留
    t = re.sub(r"Temperature\s*\(C\).*?(?=\n[A-Z]|$)", "", t, flags=re.S)

    # 3. 去掉页眉页脚或导航类词
    t = re.sub(r"\b(KARRIERE|ENGLISH|DEUTSCH|KONTAKT|ÜBER UNS|NEWS|ACCESS)\b", "", t, flags=re.I)

    # 4. 连续空行压缩
    t = re.sub(r"\n{2,}", "\n", t)

    # 5. 删除首尾多余空格
    t = t.strip()
    return t


# ========== Clients ==========
def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
    """
    Azure Embedding 客户端（Azure 上需要部署 embedding 模型）。
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
    """
    resp = azure_embed_client.embeddings.create(model=model, input=texts)
    vecs = [item.embedding for item in resp.data]
    return _pad_or_truncate(vecs, target_dim)


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
        "capabilities": {
            "type": "array",
            "items": {"type": "string"}
        },
        "projects": {
            "type": "array",
            "items": {"type": "string"}
        },
        "awards": {
            "type": "array",
            "items": {"type": "string"}
        },
        "services": {
            "type": "array",
            "items": {"type": "string"}
        },
        "notes": {"type": "string"},
    },
}

PROMPT_SYSTEM = (
    "You are a precise information extraction assistant. "
    "Given an organization brochure/manual text, extract a comprehensive JSON object that follows the provided JSON schema. "
    "Extract as much structured information as possible including:\n"
    "- Basic organization details (name, country, address, etc.)\n"
    "- Contact information (people with names, emails, phones, titles)\n"
    "- Team members and their roles\n"
    "- Facilities and equipment\n"
    "- Capabilities and competencies\n"
    "- Projects and initiatives\n"
    "- Awards and recognitions\n"
    "- Services offered\n"
    "If a field is missing, use null or an empty list. Do not add fields not in the schema. "
    "Return JSON only, no extra commentary."
)

def extract_org_json(full_text: str, deepseek_client: OpenAIPlatform, chat_model: str) -> Dict[str, Any]:
    """使用DeepSeek智能提取组织信息，严格按照Schema返回"""
    print(f"[info] 开始JSON抽取，文本长度: {len(full_text)} 字符")
    try:
        text_for_extraction = full_text
        schema_str = json.dumps(ORG_SCHEMA, indent=2, ensure_ascii=False)
        enhanced_prompt = f"""{PROMPT_SYSTEM}

Please strictly follow this JSON Schema format for your response:

{schema_str}

Critical instructions:
- Extract information ONLY if clearly present in the text
- Use null for missing string/number fields
- Use empty arrays [] for missing array fields
- Do NOT guess or infer information not explicitly stated
- Field names must exactly match the schema
- Return valid JSON only, no explanations"""

        print("[info] 使用DeepSeek进行智能信息提取...")
        rsp = deepseek_client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": f"Extract organization information from this text:\n\n{text_for_extraction}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )
        raw_content = rsp.choices[0].message.content
        print(f"[info] DeepSeek提取成功，返回内容前200字符: {raw_content[:200]}...")
        result = json.loads(raw_content)
        validated_result = ensure_schema_compliance(result)
        print(f"[info] Schema验证完成: {json.dumps(validated_result, ensure_ascii=False)[:200]}...")
        return validated_result
    except Exception as e:
        print(f"[error] DeepSeek提取失败：{e}")
        print("[warn] 返回符合Schema的空结构")
        return get_empty_schema_result()


def ensure_schema_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """确保返回的数据符合ORG_SCHEMA结构，但不进行额外推断"""
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
    """返回符合Schema的空结构"""
    return {
        "org_name": None, "country": None, "address": None, "founded_year": None,
        "size": None, "industry": None, "is_DU_member": None, "website": None,
        "contacts": [], "members": [], "facilities": [],
        "capabilities": [], "projects": [], "awards": [], "services": [], "notes": None
    }


def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
    """将抽取的组织数据扁平化为索引字段格式"""
    contacts = data.get("contacts") or []
    contacts_name = [c.get("name") for c in contacts if isinstance(c, dict) and c.get("name")]
    contacts_email = [c.get("email") for c in contacts if isinstance(c, dict) and c.get("email")]
    contacts_phone = [c.get("phone") for c in contacts if isinstance(c, dict) and c.get("phone")]

    members = data.get("members", []) or data.get("people", []) or []
    members_name = [m.get("name") for m in members if isinstance(m, dict) and m.get("name")]
    members_title = [m.get("title") for m in members if isinstance(m, dict) and m.get("title")]
    members_role = [m.get("role") for m in members if isinstance(m, dict) and m.get("role")]

    facilities = data.get("facilities", []) or []
    facilities_name = [f.get("name") for f in facilities if isinstance(f, dict) and f.get("name")]
    facilities_type = [f.get("type") for f in facilities if isinstance(f, dict) and f.get("type")]
    facilities_usage = [f.get("usage") for f in facilities if isinstance(f, dict) and f.get("usage")]

    capabilities = data.get("capabilities", []) or []
    if isinstance(capabilities, str):
        capabilities = [capabilities]
    elif not isinstance(capabilities, list):
        capabilities = []

    projects = data.get("projects", []) or data.get("key_projects", []) or []
    if isinstance(projects, str):
        projects = [projects]
    elif not isinstance(projects, list):
        projects = []

    awards = data.get("awards", []) or []
    if isinstance(awards, str):
        awards = [awards]
    elif not isinstance(awards, list):
        awards = []

    services = data.get("services", []) or []
    if isinstance(services, str):
        services = [services]
    elif not isinstance(services, list):
        services = []

    addresses = []
    if data.get("address"):
        addresses.append(data.get("address"))
    if data.get("addresses"):
        if isinstance(data.get("addresses"), list):
            addresses.extend(data.get("addresses"))
        else:
            addresses.append(str(data.get("addresses")))
    for contact in contacts:
        if isinstance(contact, dict) and contact.get("address"):
            addresses.append(contact.get("address"))

    return {
        # 基本组织信息
        "org_name": data.get("org_name"),
        "country": data.get("country"),
        "address": data.get("address"),
        "founded_year": data.get("founded_year"),
        "size": data.get("size"),
        "industry": data.get("industry"),
        "is_DU_member": data.get("is_DU_member"),
        "website": data.get("website"),

        # 人员信息
        "members_name": members_name,
        "members_title": members_title,
        "members_role": members_role,

        # 设施信息
        "facilities_name": facilities_name,
        "facilities_type": facilities_type,
        "facilities_usage": facilities_usage,

        # 能力和项目
        "capabilities": capabilities,
        "projects": projects,
        "awards": awards,
        "services": services,

        # 联系信息
        "contacts_name": contacts_name,
        "contacts_email": contacts_email,
        "contacts_phone": contacts_phone,

        # 地址和备注
        "addresses": addresses,
        "notes": data.get("notes"),

        # 页码信息（目前设为None，未来可以从PDF中提取）
        "page_from": None,
        "page_to": None,
    }


# ========== main ingest ==========
def ingest_pdf_single_index(pdf_path: str, cfg: dict):
    source_id = str(uuid.uuid4()) # 每个PDF生成唯一ID
    filename = os.path.basename(pdf_path)

    # Embedding 用 Azure（部署名）
    azure_embed_client = build_azure_embed_client(cfg)

    # Chat 用 DeepSeek
    deepseek_client = build_deepseek_chat_client(cfg)

    embed_model = cfg["embedding_model"]                 # Azure Openai Embedding“部署名”
    chat_model = cfg.get("chat_model", "deepseek-chat")  # DeepSeek 模型名
    embed_dims = int(cfg.get("embedding_dimensions", 1536))

    # Azure Search
    search = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=cfg["index_name"],
        credential=AzureKeyCredential(cfg["search_api_key"]),
    )

    # 1) PDF 提取（返回三元组）
    full_text, doc_json, blocks = extract_text_from_pdf(pdf_path, cfg)
    
    # 清理噪音文本（导航栏、:selected:等）
    full_text = clean_text(full_text)

    # 2) JSON 抽取（DeepSeek）
    if chat_model:
        try:
            semantic_text = build_semantic_text(blocks) if blocks else full_text
            text_for_llm = semantic_text if semantic_text else full_text
            struct_json = extract_org_json(text_for_llm, deepseek_client, chat_model)
        except Exception as e:
            print(f"[warn] JSON 抽取失败：{e}")
            struct_json = {}
    else:
        struct_json = {}

    flat_org = flatten_for_index(struct_json) if struct_json else {}

    # 3) chunk + embedding(Azure) + 上传
    # 动态调整chunk大小：如果文档较小，使用更小的chunk
    text_len = len(full_text)
    if text_len <= 3000:
        chunk_size = max(500, text_len // 3)  # 分成大约3个chunks
        overlap = min(100, chunk_size // 10)
    else:
        chunk_size = 5000
        overlap = 200

    print(f"文档长度: {text_len} 字符，使用chunk大小: {chunk_size}")
    chunks = chunk_text(full_text, max_chunk_size=chunk_size, overlap=overlap)
    docs_batch = []
    for i in tqdm(range(0, len(chunks), 16), desc="Embedding"):
        sub = chunks[i:i + 16]
        embs = batch_embeddings(azure_embed_client, embed_model, sub, embed_dims)
        for j, (ck, emb) in enumerate(zip(sub, embs)):
            idx = i + j
            doc = {
                "id": f"{source_id}-{idx}",  # 每个chunk都会标记相同的source_id和chunk的唯一ID
                "source_id": source_id,      # PDF文档的唯一标识
                "chunk_index": idx,          # chunk在文档中的位置
                "content": ck,               # chunk文本内容
                "filepath": os.path.abspath(pdf_path),  # PDF文件路径
                "content_vector": emb,       # Embedding向量
                **flat_org,                  # 其他的组织信息字段
            }
            docs_batch.append(doc)
        # 批量上传
        if len(docs_batch) >= 64:
            search.merge_or_upload_documents(docs_batch)
            docs_batch = []

    if docs_batch:
        search.merge_or_upload_documents(docs_batch)

    print(f"[ok] Ingested {len(chunks)} chunks for {filename} | source_id={source_id}")


def ingest_folder_batch(folder_path: str, cfg: dict):
    """批量处理文件夹中的所有PDF文件"""
    pdf_files = []
    for ext in ['*.pdf', '*.PDF']:
        pdf_files.extend(glob.glob(os.path.join(folder_path, ext)))
    
    # 去重：Windows系统中文件名大小写不敏感，会导致重复
    pdf_files = list(set(os.path.normpath(f) for f in pdf_files))
    pdf_files.sort()  # 排序保持一致的处理顺序

    if not pdf_files:
        print(f"[warn] 在 {folder_path} 中没有找到PDF文件")
        return

    print(f"[info] 找到 {len(pdf_files)} 个PDF文件:")
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"  {i}. {os.path.basename(pdf_file)}")

    success_count = 0
    error_count = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            print(f"\n[info] 处理第 {i}/{len(pdf_files)} 个文件: {os.path.basename(pdf_file)}")
            ingest_pdf_single_index(pdf_file, cfg)
            success_count += 1
            print(f"[ok] 成功处理: {os.path.basename(pdf_file)}")
        except Exception as e:
            error_count += 1
            print(f"[error] 处理失败: {os.path.basename(pdf_file)} - {e}")
            continue

    print(f"\n[info] 批量处理完成:")
    print(f"  成功: {success_count} 个文件")
    print(f"  失败: {error_count} 个文件")
    print(f"  总计: {len(pdf_files)} 个文件")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  单个文件: python embed_and_ingest_chunks.py <pdf_path> <config.json>")
        print("  批量文件夹: python embed_and_ingest_chunks.py --folder <folder_path> <config.json>")
        sys.exit(1)

    with open(sys.argv[-1], "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if len(sys.argv) == 4 and sys.argv[1] == "--folder":
        # 批量模式
        folder_path = sys.argv[2]
        ingest_folder_batch(folder_path, cfg)
    else:
        # 单文件模式
        pdf_path = sys.argv[1]
        ingest_pdf_single_index(pdf_path, cfg)



# # 提取pdf文本，组织语料为结构化格式，使用 DeepSeek 进行 JSON 抽取
# #debug 输出调试文件：输入deepseek文本、DeepSeek输出、最终验证后的结果
# # 混合模式：Embedding 用 Azure（已部署），Chat 用 DeepSeek（OpenAI 兼容）
# import os, sys, json, uuid, re, mimetypes, glob
# from typing import List, Dict, Any, Optional
# from tqdm import tqdm

# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
# from azure.ai.documentintelligence import DocumentIntelligenceClient  # 保留导入（不使用）
# from azure.ai.formrecognizer import DocumentAnalysisClient            # 使用旧客户端
# from azure.core.exceptions import ResourceNotFoundError

# # DeepSeek 走 OpenAI 兼容客户端；Azure Embedding 走 AzureOpenAI
# from openai import OpenAI as OpenAIPlatform, AzureOpenAI


# # ========== PDF utilities ==========
# def extract_text_from_pymupdf(pdf_path: str) -> str:
#     """使用PyMuPDF提取PDF文本"""
#     try:
#         import fitz
#         doc = fitz.open(pdf_path)
#         text_content = ""
#         total_pages = len(doc)
#         for page_num in range(total_pages):
#             page = doc.load_page(page_num)
#             text_content += page.get_text() + "\n"
#         doc.close()
#         print(f"[info] PyMuPDF成功提取{len(text_content)}字符（{total_pages}页）")
#         return text_content
#     except ImportError:
#         raise ImportError("PyMuPDF (fitz) 未安装，请运行: pip install PyMuPDF")
#     except Exception as e:
#         raise RuntimeError(f"PyMuPDF提取失败：{e}")


# def _build_blocks_from_result(result):
#     """从 Form Recognizer/DI 的 result 构建轻量 blocks 列表"""
#     blocks = []

#     # 段落
#     for p in getattr(result, "paragraphs", []) or []:
#         if getattr(p, "content", None):
#             page = None
#             br = getattr(p, "bounding_regions", None)
#             if br:
#                 try:
#                     page = br[0].page_number
#                 except Exception:
#                     page = getattr(br[0], "page_number", None)
#             blocks.append({"type": "paragraph", "content": p.content, "page": page})

#     # 表格 -> TSV
#     for t in getattr(result, "tables", []) or []:
#         rows = {}
#         for cell in t.cells:
#             rows.setdefault(cell.row_index, {})
#             rows[cell.row_index][cell.column_index] = (cell.content or "").strip()
#         lines = []
#         if rows:
#             max_r = max(rows.keys())
#             max_c = max(max(r.keys()) for r in rows.values()) if rows else -1
#             for r in range(max_r + 1):
#                 row = rows.get(r, {})
#                 cols = [row.get(c, "") for c in range(max_c + 1)]
#                 lines.append("\t".join(cols))
#         if lines:
#             page = None
#             br = getattr(t, "bounding_regions", None)
#             if br:
#                 try:
#                     page = br[0].page_number
#                 except Exception:
#                     page = getattr(br[0], "page_number", None)
#             blocks.append({"type": "table", "content": "\n".join(lines), "page": page})

#     # 键值对
#     for kv in getattr(result, "key_value_pairs", []) or []:
#         k = getattr(getattr(kv, "key", None), "content", None)
#         v = getattr(getattr(kv, "value", None), "content", None)
#         if k or v:
#             page = None
#             br = getattr(kv, "bounding_regions", None)
#             if br:
#                 try:
#                     page = br[0].page_number
#                 except Exception:
#                     page = getattr(br[0], "page_number", None)
#             blocks.append({"type": "kv", "content": f"{k or ''} : {v or ''}".strip(), "page": page})

#     return blocks


# def extract_text_from_document_intelligence(pdf_path, endpoint, key):
#     """使用Azure Document Intelligence提取文本（旧 SDK 客户端，稳定）"""
#     try:
#         client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
#         with open(pdf_path, "rb") as f:
#             poller = client.begin_analyze_document("prebuilt-document", document=f)
#             result = poller.result()

#         text_content = ""
#         if getattr(result, "paragraphs", None):
#             lines = [p.content for p in result.paragraphs if p.content]
#             text_content = "\n".join(lines)
#         elif getattr(result, "content", None):
#             text_content = result.content
#         else:
#             text_blocks = []
#             for table in getattr(result, "tables", []) or []:
#                 for cell in table.cells:
#                     if cell.content:
#                         text_blocks.append(cell.content)
#             text_content = "\n".join(text_blocks)

#         azure_pages = len(result.pages) if hasattr(result, 'pages') and result.pages else 0
#         print(f"[info] Azure Document Intelligence成功提取{len(text_content)}字符（{azure_pages}页）")
#         return text_content
#     except Exception as e:
#         raise RuntimeError(f"Azure Document Intelligence提取失败：{e}")


# def extract_text_from_pdf(pdf_path: str, cfg: dict):
#     """
#     返回: (full_text, doc_json, blocks)
#     - 当使用 PyMuPDF 时：doc_json=None, blocks=None
#     - 当使用 Azure DocInt 时：返回结构化后的三元组
#     """
#     method = cfg.get("pdf_extraction_method", "pymupdf").lower()
#     fallback = cfg.get("pdf_extraction_fallback", True)
#     primary = method
#     backup = "azure_docint" if method == "pymupdf" else "pymupdf"

#     print(f"[info] 使用PDF提取方法: {primary} (备选: {backup if fallback else '无'})")

#     def _docint_triplet():
#         client = DocumentAnalysisClient(endpoint=cfg["docint_endpoint"], credential=AzureKeyCredential(cfg["docint_key"]))
#         with open(pdf_path, "rb") as f:
#             poller = client.begin_analyze_document("prebuilt-document", document=f)
#             result = poller.result()
#         blocks = _build_blocks_from_result(result)
#         full_text = "\n".join(b["content"] for b in blocks if b["content"]) if blocks else (getattr(result, "content", "") or "")
#         doc_json = result.to_dict() if hasattr(result, "to_dict") else None
#         pages = len(result.pages) if getattr(result, "pages", None) else 0
#         print(f"[info] DocInt(prebuilt-document) 提取: {len(full_text)} 字符（{pages}页，块={len(blocks)}）")
#         return full_text, doc_json, blocks

#     try:
#         if primary == "pymupdf":
#             text = extract_text_from_pymupdf(pdf_path)
#             return text, None, None
#         elif primary == "azure_docint":
#             return _docint_triplet()
#         else:
#             raise ValueError(f"不支持的PDF提取方法: {primary}")
#     except Exception as e:
#         print(f"[warn] {primary} 提取失败：{e}")
#         if not fallback:
#             raise e
#         print(f"[info] 切换到备选方法: {backup}")
#         try:
#             if backup == "pymupdf":
#                 text = extract_text_from_pymupdf(pdf_path)
#                 return text, None, None
#             elif backup == "azure_docint":
#                 return _docint_triplet()
#         except Exception as ee:
#             raise RuntimeError(f"所有PDF提取方法都失败。主要方法({primary})：{e}，备选方法({backup})：{ee}")
#         raise e  # 如果没有备选方法成功，抛出原始错误


# def build_semantic_text(blocks: Optional[List[Dict[str, Any]]], max_chars=12000) -> str:
#     """将段落/表格/KV组织成较干净的抽取语料"""
#     if not blocks:
#         return ""
#     def noise(s: str) -> bool:
#         s2 = (s or "").strip().lower()
#         return bool(re.match(r"^(page \d+|\d+|contents|table of contents)$", s2))
#     paras = [b for b in blocks if b["type"] == "paragraph" and b.get("content") and not noise(b["content"])]
#     tables = [b for b in blocks if b["type"] == "table" and b.get("content")]
#     kvs    = [b for b in blocks if b["type"] == "kv" and b.get("content")]

#     parts = []
#     if paras:
#         parts.append("\n".join(p["content"] for p in paras))
#     if tables:
#         parts.append("\n".join(t["content"] for t in tables[:10]))
#     if kvs:
#         parts.append("\n".join(k["content"] for k in kvs[:100]))
#     text = "\n\n".join(parts)
#     return text[:max_chars]


# def chunk_text(text: str, max_chunk_size=5000, overlap=200) -> List[str]:
#     chunks = []
#     n = len(text)
#     if n == 0:
#         return chunks
#     overlap = max(0, min(overlap, max_chunk_size - 1))
#     start = 0
#     while start < n:
#         end = min(start + max_chunk_size, n)
#         if end < n:
#             bp = text.rfind("\n", start, end)
#             if bp == -1 or (end - bp) > 1000:
#                 bp2 = text.rfind(". ", start, end)
#                 if bp2 != -1 and (end - bp2) < 1000:
#                     bp = bp2
#             if bp != -1 and bp > start + 1000:
#                 end = bp + 1
#         chunk = text[start:end].strip()
#         if chunk:
#             chunks.append(chunk)
#         if end >= n:
#             break
#         start = max(0, end - overlap)
#         if start >= n:
#             break
#     return chunks

# def clean_text(text: str) -> str:
#     """清理提取文本中的常见网页/版面噪音"""
#     if not text:
#         return text
#     t = text

#     # 1. 去掉 :selected:、:: 等标记
#     t = re.sub(r":selected:", "", t)
#     t = re.sub(r"\s+:\s+", ": ", t)

#     # 2. 去掉多余符号与温度、图表残留
#     t = re.sub(r"Temperature\s*\(C\).*?(?=\n[A-Z]|$)", "", t, flags=re.S)

#     # 3. 去掉页眉页脚或导航类词
#     t = re.sub(r"\b(KARRIERE|ENGLISH|DEUTSCH|KONTAKT|ÜBER UNS|NEWS|ACCESS)\b", "", t, flags=re.I)

#     # 4. 连续空行压缩
#     t = re.sub(r"\n{2,}", "\n", t)

#     # 5. 删除首尾多余空格
#     t = t.strip()
#     return t



# # ========== Clients ==========
# def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
#     """
#     Azure Embedding 客户端（Azure 上需要部署 embedding 模型）。
#     cfg 需包含：openai_api_key, openai_api_version, openai_endpoint
#     """
#     return AzureOpenAI(
#         api_key=cfg["openai_api_key"],
#         api_version=cfg["openai_api_version"],
#         azure_endpoint=cfg["openai_endpoint"],
#     )

# def build_deepseek_chat_client(cfg: dict) -> OpenAIPlatform:
#     """
#     DeepSeek Chat 客户端（OpenAI 兼容）。
#     cfg 需包含：deepseek_api_key；可选 deepseek_base_url (默认 https://api.deepseek.com)
#     """
#     return OpenAIPlatform(
#         api_key=cfg["deepseek_api_key"],
#         base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com")
#     )


# # ========== Embeddings ==========
# def _pad_or_truncate(vecs: List[List[float]], target_dim: int) -> List[List[float]]:
#     fixed = []
#     for v in vecs:
#         if len(v) == target_dim:
#             fixed.append(v)
#         elif len(v) > target_dim:
#             fixed.append(v[:target_dim])
#         else:
#             fixed.append(v + [0.0] * (target_dim - len(v)))
#     return fixed

# def batch_embeddings(azure_embed_client: AzureOpenAI, model: str, texts: List[str], target_dim: int) -> List[List[float]]:
#     """
#     - 使用 Azure 部署好的 embedding （model=部署名）
#     """
#     resp = azure_embed_client.embeddings.create(model=model, input=texts)
#     vecs = [item.embedding for item in resp.data]
#     return _pad_or_truncate(vecs, target_dim)


# # ========== JSON 抽取（DeepSeek Chat）==========
# ORG_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "org_name": {"type": "string"},
#         "country": {"type": "string"},
#         "address": {"type": "string"},
#         "founded_year": {"type": ["integer", "null"]},
#         "size": {"type": "string"},
#         "industry": {"type": "string"},
#         "is_DU_member": {"type": ["boolean", "null"]},
#         "website": {"type": ["string", "null"]},
#         "contacts": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "email": {"type": ["string", "null"]},
#                     "phone": {"type": ["string", "null"]},
#                     "title": {"type": ["string", "null"]},
#                     "address": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "members": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "title": {"type": ["string", "null"]},
#                     "role": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "facilities": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "type": {"type": ["string", "null"]},
#                     "usage": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "capabilities": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "projects": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "awards": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "services": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "notes": {"type": "string"},
#     },
# }

# PROMPT_SYSTEM = (
#     "You are a precise information extraction assistant. "
#     "Given an organization brochure/manual text, extract a comprehensive JSON object that follows the provided JSON schema. "
#     "Extract as much structured information as possible including:\n"
#     "- Basic organization details (name, country, address, etc.)\n"
#     "- Contact information (people with names, emails, phones, titles)\n"
#     "- Team members and their roles\n"
#     "- Facilities and equipment\n"
#     "- Capabilities and competencies\n"
#     "- Projects and initiatives\n"
#     "- Awards and recognitions\n"
#     "- Services offered\n"
#     "If a field is missing, use null or an empty list. Do not add fields not in the schema. "
#     "Return JSON only, no extra commentary."
# )

# def extract_org_json(full_text: str, deepseek_client: OpenAIPlatform, chat_model: str, debug_prefix: str = None) -> Dict[str, Any]:
#     """使用DeepSeek智能提取组织信息，严格按照Schema返回"""
#     print(f"[info] 开始JSON抽取，文本长度: {len(full_text)} 字符")
    
#     # 保存调试文件的前缀（基于PDF文件名）
#     if debug_prefix:
#         debug_dir = "debug_outputs"
#         os.makedirs(debug_dir, exist_ok=True)
        
#         # 保存输入给DeepSeek的语义文本
#         semantic_text_file = os.path.join(debug_dir, f"{debug_prefix}_semantic_text.txt")
#         with open(semantic_text_file, "w", encoding="utf-8") as f:
#             f.write("=== 输入给DeepSeek的语义文本 ===\n")
#             f.write(f"文本长度: {len(full_text)} 字符\n")
#             f.write("="*50 + "\n\n")
#             f.write(full_text)
#         print(f"[debug] 语义文本已保存到: {semantic_text_file}")
    
#     try:
#         text_for_extraction = full_text
#         schema_str = json.dumps(ORG_SCHEMA, indent=2, ensure_ascii=False)
#         enhanced_prompt = f"""{PROMPT_SYSTEM}

# Please strictly follow this JSON Schema format for your response:

# {schema_str}

# Critical instructions:
# - Extract information ONLY if clearly present in the text
# - Use null for missing string/number fields
# - Use empty arrays [] for missing array fields
# - Do NOT guess or infer information not explicitly stated
# - Field names must exactly match the schema
# - Return valid JSON only, no explanations"""

#         print("[info] 使用DeepSeek进行智能信息提取...")
#         rsp = deepseek_client.chat.completions.create(
#             model=chat_model,
#             messages=[
#                 {"role": "system", "content": enhanced_prompt},
#                 {"role": "user", "content": f"Extract organization information from this text:\n\n{text_for_extraction}"},
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.1,
#             max_tokens=2048,
#         )
#         raw_content = rsp.choices[0].message.content
#         print(f"[info] DeepSeek提取成功，返回内容前200字符: {raw_content[:200]}...")
        
#         # 保存DeepSeek的原始JSON输出
#         if debug_prefix:
#             json_output_file = os.path.join(debug_dir, f"{debug_prefix}_deepseek_output.txt")
#             with open(json_output_file, "w", encoding="utf-8") as f:
#                 f.write("=== DeepSeek原始JSON输出 ===\n")
#                 f.write(f"输出长度: {len(raw_content)} 字符\n")
#                 f.write("="*50 + "\n\n")
#                 # 格式化JSON便于阅读
#                 try:
#                     parsed_json = json.loads(raw_content)
#                     formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
#                     f.write(formatted_json)
#                 except:
#                     # 如果JSON解析失败，直接写入原始内容
#                     f.write(raw_content)
#             print(f"[debug] DeepSeek输出已保存到: {json_output_file}")
        
#         result = json.loads(raw_content)
#         validated_result = ensure_schema_compliance(result)
#         print(f"[info] Schema验证完成: {json.dumps(validated_result, ensure_ascii=False)[:200]}...")
        
#         # 保存最终验证后的结果
#         if debug_prefix:
#             final_result_file = os.path.join(debug_dir, f"{debug_prefix}_final_result.txt")
#             with open(final_result_file, "w", encoding="utf-8") as f:
#                 f.write("=== 最终验证后的结果 ===\n")
#                 f.write("="*50 + "\n\n")
#                 formatted_result = json.dumps(validated_result, indent=2, ensure_ascii=False)
#                 f.write(formatted_result)
#             print(f"[debug] 最终结果已保存到: {final_result_file}")
        
#         return validated_result
        
#     except Exception as e:
#         print(f"[error] DeepSeek提取失败：{e}")
#         print("[warn] 返回符合Schema的空结构")
#         return get_empty_schema_result()


# def ensure_schema_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
#     """确保返回的数据符合ORG_SCHEMA结构，但不进行额外推断"""
#     schema_defaults = {
#         "org_name": None, "country": None, "address": None, "founded_year": None,
#         "size": None, "industry": None, "is_DU_member": None, "website": None,
#         "contacts": [], "members": [], "facilities": [],
#         "capabilities": [], "projects": [], "awards": [], "services": [], "notes": None
#     }
#     result = {}
#     for field, default_value in schema_defaults.items():
#         if field in data and data[field] is not None:
#             value = data[field]
#             if field in ["contacts", "members", "facilities"]:
#                 result[field] = [item for item in value] if isinstance(value, list) else []
#             elif field in ["capabilities", "projects", "awards", "services"]:
#                 if isinstance(value, list):
#                     result[field] = [str(item) for item in value if item]
#                 elif isinstance(value, str) and value.strip():
#                     result[field] = [value.strip()]
#                 else:
#                     result[field] = []
#             elif field == "founded_year":
#                 if isinstance(value, int):
#                     result[field] = value
#                 elif isinstance(value, str) and value.isdigit():
#                     result[field] = int(value)
#                 else:
#                     result[field] = None
#             elif field == "is_DU_member":
#                 if isinstance(value, bool):
#                     result[field] = value
#                 elif isinstance(value, str):
#                     result[field] = value.lower() in ["true", "yes", "1", "是"]
#                 else:
#                     result[field] = None
#             else:
#                 result[field] = str(value).strip() if value else None
#         else:
#             result[field] = default_value
#     return result


# def get_empty_schema_result() -> Dict[str, Any]:
#     """返回符合Schema的空结构"""
#     return {
#         "org_name": None, "country": None, "address": None, "founded_year": None,
#         "size": None, "industry": None, "is_DU_member": None, "website": None,
#         "contacts": [], "members": [], "facilities": [],
#         "capabilities": [], "projects": [], "awards": [], "services": [], "notes": None
#     }


# def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
#     """将抽取的组织数据扁平化为索引字段格式"""
#     contacts = data.get("contacts") or []
#     contacts_name = [c.get("name") for c in contacts if isinstance(c, dict) and c.get("name")]
#     contacts_email = [c.get("email") for c in contacts if isinstance(c, dict) and c.get("email")]
#     contacts_phone = [c.get("phone") for c in contacts if isinstance(c, dict) and c.get("phone")]

#     members = data.get("members", []) or data.get("people", []) or []
#     members_name = [m.get("name") for m in members if isinstance(m, dict) and m.get("name")]
#     members_title = [m.get("title") for m in members if isinstance(m, dict) and m.get("title")]
#     members_role = [m.get("role") for m in members if isinstance(m, dict) and m.get("role")]

#     facilities = data.get("facilities", []) or []
#     facilities_name = [f.get("name") for f in facilities if isinstance(f, dict) and f.get("name")]
#     facilities_type = [f.get("type") for f in facilities if isinstance(f, dict) and f.get("type")]
#     facilities_usage = [f.get("usage") for f in facilities if isinstance(f, dict) and f.get("usage")]

#     capabilities = data.get("capabilities", []) or []
#     if isinstance(capabilities, str):
#         capabilities = [capabilities]
#     elif not isinstance(capabilities, list):
#         capabilities = []

#     projects = data.get("projects", []) or data.get("key_projects", []) or []
#     if isinstance(projects, str):
#         projects = [projects]
#     elif not isinstance(projects, list):
#         projects = []

#     awards = data.get("awards", []) or []
#     if isinstance(awards, str):
#         awards = [awards]
#     elif not isinstance(awards, list):
#         awards = []

#     services = data.get("services", []) or []
#     if isinstance(services, str):
#         services = [services]
#     elif not isinstance(services, list):
#         services = []

#     addresses = []
#     if data.get("address"):
#         addresses.append(data.get("address"))
#     if data.get("addresses"):
#         if isinstance(data.get("addresses"), list):
#             addresses.extend(data.get("addresses"))
#         else:
#             addresses.append(str(data.get("addresses")))
#     for contact in contacts:
#         if isinstance(contact, dict) and contact.get("address"):
#             addresses.append(contact.get("address"))

#     return {
#         # 基本组织信息
#         "org_name": data.get("org_name"),
#         "country": data.get("country"),
#         "address": data.get("address"),
#         "founded_year": data.get("founded_year"),
#         "size": data.get("size"),
#         "industry": data.get("industry"),
#         "is_DU_member": data.get("is_DU_member"),
#         "website": data.get("website"),

#         # 人员信息
#         "members_name": members_name,
#         "members_title": members_title,
#         "members_role": members_role,

#         # 设施信息
#         "facilities_name": facilities_name,
#         "facilities_type": facilities_type,
#         "facilities_usage": facilities_usage,

#         # 能力和项目
#         "capabilities": capabilities,
#         "projects": projects,
#         "awards": awards,
#         "services": services,

#         # 联系信息
#         "contacts_name": contacts_name,
#         "contacts_email": contacts_email,
#         "contacts_phone": contacts_phone,

#         # 地址和备注
#         "addresses": addresses,
#         "notes": data.get("notes"),

#         # 页码信息（目前设为None，未来可以从PDF中提取）
#         "page_from": None,
#         "page_to": None,
#     }


# # ========== main ingest ==========
# def ingest_pdf_single_index(pdf_path: str, cfg: dict):
#     source_id = str(uuid.uuid4()) # 每个PDF生成唯一ID
#     filename = os.path.basename(pdf_path)

#     # Embedding 用 Azure（部署名）
#     azure_embed_client = build_azure_embed_client(cfg)

#     # Chat 用 DeepSeek
#     deepseek_client = build_deepseek_chat_client(cfg)

#     embed_model = cfg["embedding_model"]                 # Azure Openai Embedding“部署名”
#     chat_model = cfg.get("chat_model", "deepseek-chat")  # DeepSeek 模型名
#     embed_dims = int(cfg.get("embedding_dimensions", 1536))

#     # Azure Search
#     search = SearchClient(
#         endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
#         index_name=cfg["index_name"],
#         credential=AzureKeyCredential(cfg["search_api_key"]),
#     )

#     # 1) PDF 提取（返回三元组）
#     full_text, doc_json, blocks = extract_text_from_pdf(pdf_path, cfg)
#     # 清理噪音文本（导航栏、:selected:等）
#     full_text = clean_text(full_text)

#     # 2) JSON 抽取（DeepSeek）
#     if chat_model:
#         try:
#             semantic_text = build_semantic_text(blocks) if blocks else full_text
#             text_for_llm = semantic_text if semantic_text else full_text
#
#             # 为调试创建文件名前缀（去掉路径和扩展名）
#             debug_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
            
#             struct_json = extract_org_json(text_for_llm, deepseek_client, chat_model, debug_prefix)
#         except Exception as e:
#             print(f"[warn] JSON 抽取失败：{e}")
#             struct_json = {}
#     else:
#         struct_json = {}

#     flat_org = flatten_for_index(struct_json) if struct_json else {}

#     # 3) chunk + embedding(Azure) + 上传
#     # 动态调整chunk大小：如果文档较小，使用更小的chunk
#     text_len = len(full_text)
#     if text_len <= 3000:
#         chunk_size = max(500, text_len // 3)  # 分成大约3个chunks
#         overlap = min(100, chunk_size // 10)
#     else:
#         chunk_size = 5000
#         overlap = 200

#     print(f"文档长度: {text_len} 字符，使用chunk大小: {chunk_size}")
#     chunks = chunk_text(full_text, max_chunk_size=chunk_size, overlap=overlap)
#     docs_batch = []
#     for i in tqdm(range(0, len(chunks), 16), desc="Embedding"):
#         sub = chunks[i:i + 16]
#         embs = batch_embeddings(azure_embed_client, embed_model, sub, embed_dims)
#         for j, (ck, emb) in enumerate(zip(sub, embs)):
#             idx = i + j
#             doc = {
#                 "id": f"{source_id}-{idx}",  # 每个chunk都会标记相同的source_id和chunk的唯一ID
#                 "source_id": source_id,      # PDF文档的唯一标识
#                 "chunk_index": idx,          # chunk在文档中的位置
#                 "content": ck,               # chunk文本内容
#                 "filepath": os.path.abspath(pdf_path),  # PDF文件路径
#                 "content_vector": emb,       # Embedding向量
#                 **flat_org,                  # 其他的组织信息字段
#             }
#             docs_batch.append(doc)
#         # 批量上传
#         if len(docs_batch) >= 64:
#             search.merge_or_upload_documents(docs_batch)
#             docs_batch = []

#     if docs_batch:
#         search.merge_or_upload_documents(docs_batch)

#     print(f"[ok] Ingested {len(chunks)} chunks for {filename} | source_id={source_id}")


# def ingest_folder_batch(folder_path: str, cfg: dict):
#     """批量处理文件夹中的所有PDF文件"""
#     pdf_files = []
#     for ext in ['*.pdf', '*.PDF']:
#         pdf_files.extend(glob.glob(os.path.join(folder_path, ext)))
    
#     # 去重：Windows系统中文件名大小写不敏感，会导致重复
#     pdf_files = list(set(os.path.normpath(f) for f in pdf_files))
#     pdf_files.sort()  # 排序保持一致的处理顺序

#     if not pdf_files:
#         print(f"[warn] 在 {folder_path} 中没有找到PDF文件")
#         return

#     print(f"[info] 找到 {len(pdf_files)} 个PDF文件:")
#     for i, pdf_file in enumerate(pdf_files, 1):
#         print(f"  {i}. {os.path.basename(pdf_file)}")

#     success_count = 0
#     error_count = 0

#     for i, pdf_file in enumerate(pdf_files, 1):
#         try:
#             print(f"\n[info] 处理第 {i}/{len(pdf_files)} 个文件: {os.path.basename(pdf_file)}")
#             ingest_pdf_single_index(pdf_file, cfg)
#             success_count += 1
#             print(f"[ok] 成功处理: {os.path.basename(pdf_file)}")
#         except Exception as e:
#             error_count += 1
#             print(f"[error] 处理失败: {os.path.basename(pdf_file)} - {e}")
#             continue

#     print(f"\n[info] 批量处理完成:")
#     print(f"  成功: {success_count} 个文件")
#     print(f"  失败: {error_count} 个文件")
#     print(f"  总计: {len(pdf_files)} 个文件")


# if __name__ == "__main__":
#     if len(sys.argv) < 3:
#         print("Usage:")
#         print("  单个文件: python embed_and_ingest_chunks.py <pdf_path> <config.json>")
#         print("  批量文件夹: python embed_and_ingest_chunks.py --folder <folder_path> <config.json>")
#         sys.exit(1)

#     with open(sys.argv[-1], "r", encoding="utf-8") as f:
#         cfg = json.load(f)

#     if len(sys.argv) == 4 and sys.argv[1] == "--folder":
#         # 批量模式
#         folder_path = sys.argv[2]
#         ingest_folder_batch(folder_path, cfg)
#     else:
#         # 单文件模式
#         pdf_path = sys.argv[1]
#         ingest_pdf_single_index(pdf_path, cfg)




# 提取pdf纯文本

# # 混合模式：Embedding 用 Azure（已部署），Chat 用 DeepSeek（OpenAI 兼容）
# import os, sys, json, uuid, re, mimetypes, glob
# from typing import List, Dict, Any
# from tqdm import tqdm

# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
# from azure.ai.documentintelligence import DocumentIntelligenceClient
# from azure.ai.formrecognizer import DocumentAnalysisClient
# from azure.core.exceptions import ResourceNotFoundError

# # DeepSeek 走 OpenAI 兼容客户端；Azure Embedding 走 AzureOpenAI
# from openai import OpenAI as OpenAIPlatform, AzureOpenAI


# # ========== PDF utilities ==========
# def extract_text_from_pymupdf(pdf_path: str) -> str:
#     """使用PyMuPDF提取PDF文本"""
#     try:
#         import fitz
#         doc = fitz.open(pdf_path)
#         text_content = ""
#         total_pages = len(doc)
#         for page_num in range(total_pages):
#             page = doc.load_page(page_num)
#             text_content += page.get_text() + "\n"
#         doc.close()
#         print(f"[info] PyMuPDF成功提取{len(text_content)}字符（{total_pages}页）")
#         return text_content
#     except ImportError:
#         raise ImportError("PyMuPDF (fitz) 未安装，请运行: pip install PyMuPDF")
#     except Exception as e:
#         raise RuntimeError(f"PyMuPDF提取失败：{e}")

# def extract_text_from_document_intelligence(pdf_path, endpoint, key):
#     """使用Azure Document Intelligence提取文本"""
#     try:
#         client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
#         with open(pdf_path, "rb") as f:
#             poller = client.begin_analyze_document("prebuilt-document", document=f)
#             result = poller.result()

#         text_content = ""
#         if getattr(result, "paragraphs", None):
#             lines = [p.content for p in result.paragraphs if p.content]
#             text_content = "\n".join(lines)
#         elif getattr(result, "content", None):
#             text_content = result.content
#         else:
#             # 兜底：从表格提取
#             text_blocks = []
#             for table in getattr(result, "tables", []) or []:
#                 for cell in table.cells:
#                     if cell.content:
#                         text_blocks.append(cell.content)
#             text_content = "\n".join(text_blocks)
        
#         azure_pages = len(result.pages) if hasattr(result, 'pages') and result.pages else 0
#         print(f"[info] Azure Document Intelligence成功提取{len(text_content)}字符（{azure_pages}页）")
#         return text_content
        
#     except Exception as e:
#         raise RuntimeError(f"Azure Document Intelligence提取失败：{e}")

# def extract_text_from_pdf(pdf_path: str, cfg: dict) -> str:
#     """
#     根据配置选择PDF文本提取方法
    
#     cfg 支持的配置项：
#     - pdf_extraction_method: "pymupdf" | "azure_docint" (默认: "pymupdf")  
#     - pdf_extraction_fallback: true | false (默认: true)
#     """
#     method = cfg.get("pdf_extraction_method", "pymupdf").lower()
#     fallback = cfg.get("pdf_extraction_fallback", True)
    
#     primary_method = method
#     backup_method = "azure_docint" if method == "pymupdf" else "pymupdf"
    
#     print(f"[info] 使用PDF提取方法: {primary_method} (备选: {backup_method if fallback else '无'})")
    
#     # 尝试主要方法
#     try:
#         if primary_method == "pymupdf":
#             return extract_text_from_pymupdf(pdf_path)
#         elif primary_method == "azure_docint":
#             return extract_text_from_document_intelligence(
#                 pdf_path, cfg["docint_endpoint"], cfg["docint_key"]
#             )
#         else:
#             raise ValueError(f"不支持的PDF提取方法: {primary_method}")
    
#     except Exception as e:
#         print(f"[warn] {primary_method} 提取失败：{e}")
        
#         if not fallback:
#             raise e
        
#         # 尝试备选方法
#         print(f"[info] 切换到备选方法: {backup_method}")
#         try:
#             if backup_method == "pymupdf":
#                 return extract_text_from_pymupdf(pdf_path)
#             elif backup_method == "azure_docint":
#                 return extract_text_from_document_intelligence(
#                     pdf_path, cfg["docint_endpoint"], cfg["docint_key"]
#                 )
#         except Exception as ee:
#             raise RuntimeError(f"所有PDF提取方法都失败了。主要方法({primary_method})：{e}，备选方法({backup_method})：{ee}")
        
#         raise e  # 如果没有备选方法成功，抛出原始错误


# def chunk_text(text: str, max_chunk_size=5000, overlap=200) -> List[str]:
#     chunks = []
#     n = len(text)
#     if n == 0:
#         return chunks
#     overlap = max(0, min(overlap, max_chunk_size - 1))
#     start = 0
#     while start < n:
#         end = min(start + max_chunk_size, n)
#         if end < n:
#             bp = text.rfind("\n", start, end)
#             if bp == -1 or (end - bp) > 1000:
#                 bp2 = text.rfind(". ", start, end)
#                 if bp2 != -1 and (end - bp2) < 1000:
#                     bp = bp2
#             if bp != -1 and bp > start + 1000:
#                 end = bp + 1
#         chunk = text[start:end].strip()
#         if chunk:
#             chunks.append(chunk)
#         if end >= n:
#             break
#         start = max(0, end - overlap)
#         if start >= n:
#             break
#     return chunks

# def clean_text(text: str) -> str:
#     """清理提取文本中的常见网页/版面噪音"""
#     if not text:
#         return text
#     t = text

#     # 1. 去掉 :selected:、:: 等标记
#     t = re.sub(r":selected:", "", t)
#     t = re.sub(r"\s+:\s+", ": ", t)

#     # 2. 去掉多余符号与温度、图表残留
#     t = re.sub(r"Temperature\s*\(C\).*?(?=\n[A-Z]|$)", "", t, flags=re.S)

#     # 3. 去掉页眉页脚或导航类词
#     t = re.sub(r"\b(KARRIERE|ENGLISH|DEUTSCH|KONTAKT|ÜBER UNS|NEWS|ACCESS)\b", "", t, flags=re.I)

#     # 4. 连续空行压缩
#     t = re.sub(r"\n{2,}", "\n", t)

#     # 5. 删除首尾多余空格
#     t = t.strip()
#     return t


# # ========== Clients ==========
# def build_azure_embed_client(cfg: dict) -> AzureOpenAI:
#     """
#     Azure Embedding 客户端（Azure 上需要部署 embedding 模型）。
#     cfg 需包含：openai_api_key, openai_api_version, openai_endpoint
#     """
#     return AzureOpenAI(
#         api_key=cfg["openai_api_key"],
#         api_version=cfg["openai_api_version"],
#         azure_endpoint=cfg["openai_endpoint"],
#     )

# def build_deepseek_chat_client(cfg: dict) -> OpenAIPlatform:
#     """
#     DeepSeek Chat 客户端（OpenAI 兼容）。
#     cfg 需包含：deepseek_api_key；可选 deepseek_base_url (默认 https://api.deepseek.com)
#     """
#     return OpenAIPlatform(
#         api_key=cfg["deepseek_api_key"],
#         base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com")
#     )


# # ========== Embeddings ==========
# def _pad_or_truncate(vecs: List[List[float]], target_dim: int) -> List[List[float]]:
#     fixed = []
#     for v in vecs:
#         if len(v) == target_dim:
#             fixed.append(v)
#         elif len(v) > target_dim:
#             fixed.append(v[:target_dim])
#         else:
#             fixed.append(v + [0.0] * (target_dim - len(v)))
#     return fixed

# def batch_embeddings(azure_embed_client: AzureOpenAI, model: str, texts: List[str], target_dim: int) -> List[List[float]]:
#     """
#     - 使用 Azure 部署好的 embedding （model=部署名）
#     """
#     resp = azure_embed_client.embeddings.create(model=model, input=texts)
#     vecs = [item.embedding for item in resp.data]
#     return _pad_or_truncate(vecs, target_dim)


# # ========== JSON 抽取（DeepSeek Chat）==========
# ORG_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "org_name": {"type": "string"},
#         "country": {"type": "string"},
#         "address": {"type": "string"},
#         "founded_year": {"type": ["integer", "null"]},
#         "size": {"type": "string"},
#         "industry": {"type": "string"},
#         "is_DU_member": {"type": ["boolean", "null"]},
#         "website": {"type": ["string", "null"]},
#         "contacts": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "email": {"type": ["string", "null"]},
#                     "phone": {"type": ["string", "null"]},
#                     "title": {"type": ["string", "null"]},
#                     "address": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "members": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "title": {"type": ["string", "null"]},
#                     "role": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "facilities": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "type": {"type": ["string", "null"]},
#                     "usage": {"type": ["string", "null"]},
#                 },
#             },
#         },
#         "capabilities": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "projects": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "awards": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "services": {
#             "type": "array",
#             "items": {"type": "string"}
#         },
#         "notes": {"type": "string"},
#     },
# }

# PROMPT_SYSTEM = (
#     "You are a precise information extraction assistant. "
#     "Given an organization brochure/manual text, extract a comprehensive JSON object that follows the provided JSON schema. "
#     "Extract as much structured information as possible including:\n"
#     "- Basic organization details (name, country, address, etc.)\n"
#     "- Contact information (people with names, emails, phones, titles)\n"
#     "- Team members and their roles\n"
#     "- Facilities and equipment\n"
#     "- Capabilities and competencies\n"
#     "- Projects and initiatives\n"
#     "- Awards and recognitions\n"
#     "- Services offered\n"
#     "If a field is missing, use null or an empty list. Do not add fields not in the schema. "
#     "Return JSON only, no extra commentary."
# )

# def extract_org_json(full_text: str, deepseek_client: OpenAIPlatform, chat_model: str) -> Dict[str, Any]:
#     """使用DeepSeek智能提取组织信息，严格按照Schema返回"""
#     print(f"[info] 开始JSON抽取，文本长度: {len(full_text)} 字符")
    
#     try:
#         # 限制文本长度避免token超限
#         # text_for_extraction = full_text[:8000] if len(full_text) > 8000 else full_text
#         text_for_extraction = full_text
#         # 将Schema转换为字符串，指导DeepSeek输出
#         schema_str = json.dumps(ORG_SCHEMA, indent=2, ensure_ascii=False)
        
#         # 简化的系统提示，专注于智能提取
#         enhanced_prompt = f"""{PROMPT_SYSTEM}

# Please strictly follow this JSON Schema format for your response:

# {schema_str}

# Critical instructions:
# - Extract information ONLY if clearly present in the text
# - Use null for missing string/number fields
# - Use empty arrays [] for missing array fields  
# - Do NOT guess or infer information not explicitly stated
# - Field names must exactly match the schema
# - Return valid JSON only, no explanations"""
        
#         print("[info] 使用DeepSeek进行智能信息提取...")
#         rsp = deepseek_client.chat.completions.create(
#             model=chat_model,
#             messages=[
#                 {"role": "system", "content": enhanced_prompt},
#                 {"role": "user", "content": f"Extract organization information from this text:\n\n{text_for_extraction}"},
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.1,
#             max_tokens=2048,
#         )
#         raw_content = rsp.choices[0].message.content
#         print(f"[info] DeepSeek提取成功，返回内容前200字符: {raw_content[:200]}...")
        
#         result = json.loads(raw_content)
        
#         # 简单验证Schema字段完整性
#         validated_result = ensure_schema_compliance(result)
#         print(f"[info] Schema验证完成: {json.dumps(validated_result, ensure_ascii=False)[:200]}...")
        
#         return validated_result
        
#     except Exception as e:
#         print(f"[error] DeepSeek提取失败：{e}")
        
#         # 返回符合Schema的空结构
#         print("[warn] 返回符合Schema的空结构")
#         return get_empty_schema_result()

# def ensure_schema_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
#     """确保返回的数据符合ORG_SCHEMA结构，但不进行额外推断"""
    
#     # 定义Schema中所有字段的默认空值
#     schema_defaults = {
#         "org_name": None,
#         "country": None, 
#         "address": None,
#         "founded_year": None,
#         "size": None,
#         "industry": None,
#         "is_DU_member": None,
#         "website": None,
#         "contacts": [],
#         "members": [],
#         "facilities": [],
#         "capabilities": [],
#         "projects": [],
#         "awards": [],
#         "services": [],
#         "notes": None
#     }
    
#     result = {}
    
#     # 处理每个字段，确保类型正确
#     for field, default_value in schema_defaults.items():
#         if field in data and data[field] is not None:
#             value = data[field]
            
#             # 根据字段类型进行基本验证
#             if field in ["contacts", "members", "facilities"]:
#                 # 对象数组字段
#                 if isinstance(value, list):
#                     result[field] = [item for item in value if isinstance(item, dict)]
#                 else:
#                     result[field] = []
                    
#             elif field in ["capabilities", "projects", "awards", "services"]:
#                 # 字符串数组字段
#                 if isinstance(value, list):
#                     result[field] = [str(item) for item in value if item]
#                 elif isinstance(value, str) and value.strip():
#                     result[field] = [value.strip()]
#                 else:
#                     result[field] = []
                    
#             elif field == "founded_year":
#                 # 整数字段
#                 if isinstance(value, int):
#                     result[field] = value
#                 elif isinstance(value, str) and value.isdigit():
#                     result[field] = int(value)
#                 else:
#                     result[field] = None
                    
#             elif field == "is_DU_member":
#                 # 布尔字段
#                 if isinstance(value, bool):
#                     result[field] = value
#                 elif isinstance(value, str):
#                     result[field] = value.lower() in ["true", "yes", "1", "是"]
#                 else:
#                     result[field] = None
                    
#             else:
#                 # 字符串字段
#                 result[field] = str(value).strip() if value else None
#         else:
#             # 使用默认空值
#             result[field] = default_value
    
#     return result

# def get_empty_schema_result() -> Dict[str, Any]:
#     """返回符合Schema的空结构"""
#     return {
#         "org_name": None,
#         "country": None,
#         "address": None,
#         "founded_year": None,
#         "size": None,
#         "industry": None,
#         "is_DU_member": None,
#         "website": None,
#         "contacts": [],
#         "members": [],
#         "facilities": [],
#         "capabilities": [],
#         "projects": [],
#         "awards": [],
#         "services": [],
#         "notes": None
#     }

# def flatten_for_index(data: Dict[str, Any]) -> Dict[str, Any]:
#     """将抽取的组织数据扁平化为索引字段格式"""
    
#     # 处理contacts数组
#     contacts = data.get("contacts") or []
#     contacts_name = [c.get("name") for c in contacts if c.get("name")]
#     contacts_email = [c.get("email") for c in contacts if c.get("email")]
#     contacts_phone = [c.get("phone") for c in contacts if c.get("phone")]
    
#     # 处理members数组（如果存在）
#     members = data.get("members", []) or data.get("people", []) or []
#     members_name = [m.get("name") for m in members if isinstance(m, dict) and m.get("name")]
#     members_title = [m.get("title") for m in members if isinstance(m, dict) and m.get("title")]
#     members_role = [m.get("role") for m in members if isinstance(m, dict) and m.get("role")]
    
#     # 处理facilities数组（如果存在）
#     facilities = data.get("facilities", []) or []
#     facilities_name = [f.get("name") for f in facilities if isinstance(f, dict) and f.get("name")]
#     facilities_type = [f.get("type") for f in facilities if isinstance(f, dict) and f.get("type")]
#     facilities_usage = [f.get("usage") for f in facilities if isinstance(f, dict) and f.get("usage")]
    
#     # 处理其他数组字段
#     capabilities = data.get("capabilities", []) or []
#     if isinstance(capabilities, str):
#         capabilities = [capabilities]
#     elif not isinstance(capabilities, list):
#         capabilities = []
        
#     projects = data.get("projects", []) or data.get("key_projects", []) or []
#     if isinstance(projects, str):
#         projects = [projects]
#     elif not isinstance(projects, list):
#         projects = []
        
#     awards = data.get("awards", []) or []
#     if isinstance(awards, str):
#         awards = [awards]
#     elif not isinstance(awards, list):
#         awards = []
        
#     services = data.get("services", []) or []
#     if isinstance(services, str):
#         services = [services]
#     elif not isinstance(services, list):
#         services = []
        
#     # 处理addresses（可能来自多个源）
#     addresses = []
#     if data.get("address"):
#         addresses.append(data.get("address"))
#     if data.get("addresses"):
#         if isinstance(data.get("addresses"), list):
#             addresses.extend(data.get("addresses"))
#         else:
#             addresses.append(str(data.get("addresses")))
    
#     # 从contacts中提取地址
#     for contact in contacts:
#         if isinstance(contact, dict) and contact.get("address"):
#             addresses.append(contact.get("address"))
    
#     return {
#         # 基本组织信息
#         "org_name": data.get("org_name"),
#         "country": data.get("country"),
#         "address": data.get("address"),
#         "founded_year": data.get("founded_year"),
#         "size": data.get("size"),
#         "industry": data.get("industry"),
#         "is_DU_member": data.get("is_DU_member"),
#         "website": data.get("website"),
        
#         # 人员信息
#         "members_name": members_name,
#         "members_title": members_title,
#         "members_role": members_role,
        
#         # 设施信息
#         "facilities_name": facilities_name,
#         "facilities_type": facilities_type,
#         "facilities_usage": facilities_usage,
        
#         # 能力和项目
#         "capabilities": capabilities,
#         "projects": projects,
#         "awards": awards,
#         "services": services,
        
#         # 联系信息
#         "contacts_name": contacts_name,
#         "contacts_email": contacts_email,
#         "contacts_phone": contacts_phone,
        
#         # 地址和备注
#         "addresses": addresses,
#         "notes": data.get("notes"),
        
#         # 页码信息（目前设为None，未来可以从PDF中提取）
#         "page_from": None,
#         "page_to": None,
#     }


# # ========== main ingest ==========
# def ingest_pdf_single_index(pdf_path: str, cfg: dict):
#     source_id = str(uuid.uuid4()) # 每个PDF生成唯一ID
#     filename = os.path.basename(pdf_path)

#     # Embedding 用 Azure（部署名）
#     azure_embed_client = build_azure_embed_client(cfg)

#     # Chat 用 DeepSeek
#     deepseek_client = build_deepseek_chat_client(cfg)

#     embed_model = cfg["embedding_model"]                 # Azure Openai Embedding“部署名”
#     chat_model = cfg.get("chat_model", "deepseek-chat")  # DeepSeek 模型名
#     embed_dims = int(cfg.get("embedding_dimensions", 1536))

#     # Azure Search
#     search = SearchClient(
#         endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
#         index_name=cfg["index_name"],
#         credential=AzureKeyCredential(cfg["search_api_key"]),
#     )

#     # 1) PDF 提取文字（根据配置选择方法）
#     full_text = extract_text_from_pdf(pdf_path, cfg)

#     # 2) JSON 抽取（DeepSeek）
#     if chat_model:
#         try:
#             struct_json = extract_org_json(full_text, deepseek_client, chat_model)
#         except Exception as e:
#             print(f"[warn] JSON 抽取失败：{e}")
#             struct_json = {}
#     else:
#         struct_json = {}

#     flat_org = flatten_for_index(struct_json) if struct_json else {}

#     # 3) chunk + embedding(Azure) + 上传
#     # 动态调整chunk大小：如果文档较小，使用更小的chunk
#     text_len = len(full_text)
#     if text_len <= 3000:
#         chunk_size = max(500, text_len // 3)  # 分成大约3个chunks
#         overlap = min(100, chunk_size // 10)
#     else:
#         chunk_size = 5000
#         overlap = 200
    
#     print(f"文档长度: {text_len} 字符，使用chunk大小: {chunk_size}")
#     chunks = chunk_text(full_text, max_chunk_size=chunk_size, overlap=overlap)
#     docs_batch = []
#     for i in tqdm(range(0, len(chunks), 16), desc="Embedding"):
#         sub = chunks[i:i + 16]
#         embs = batch_embeddings(azure_embed_client, embed_model, sub, embed_dims)
#         for j, (ck, emb) in enumerate(zip(sub, embs)):
#             idx = i + j
#             doc = {
#                 "id": f"{source_id}-{idx}",  # 每个chunk都会标记相同的source_id和chunk的唯一ID
#                 "source_id": source_id,      # PDF文档的唯一标识
#                 "chunk_index": idx,          # chunk在文档中的位置
#                 "content": ck,               # chunk文本内容
#                 "filepath": os.path.abspath(pdf_path),  # PDF文件路径
#                 "content_vector": emb,       # Embedding向量
#                 **flat_org,                  # 其他的组织信息字段
#             }
#             docs_batch.append(doc)
#         # 批量上传
#         if len(docs_batch) >= 64:
#             search.merge_or_upload_documents(docs_batch)
#             docs_batch = []

#     if docs_batch:
#         search.merge_or_upload_documents(docs_batch)

#     print(f"[ok] Ingested {len(chunks)} chunks for {filename} | source_id={source_id}")


# def ingest_folder_batch(folder_path: str, cfg: dict):
#     """批量处理文件夹中的所有PDF文件"""
#     pdf_files = []
#     for ext in ['*.pdf', '*.PDF']:
#         pdf_files.extend(glob.glob(os.path.join(folder_path, ext)))
#
#     # 去重：Windows系统中文件名大小写不敏感，会导致重复
#     pdf_files = list(set(os.path.normpath(f) for f in pdf_files))
#     pdf_files.sort()  # 排序保持一致的处理顺序
#
#     if not pdf_files:
#         print(f"[warn] 在 {folder_path} 中没有找到PDF文件")
#         return
#
#     print(f"[info] 找到 {len(pdf_files)} 个PDF文件:")
#     for i, pdf_file in enumerate(pdf_files, 1):
#         print(f"  {i}. {os.path.basename(pdf_file)}")
#
#     success_count = 0
#     error_count = 0

#     for i, pdf_file in enumerate(pdf_files, 1):
#         try:
#             print(f"\n[info] 处理第 {i}/{len(pdf_files)} 个文件: {os.path.basename(pdf_file)}")
#             ingest_pdf_single_index(pdf_file, cfg)
#             success_count += 1
#             print(f"[ok] 成功处理: {os.path.basename(pdf_file)}")
#         except Exception as e:
#             error_count += 1
#             print(f"[error] 处理失败: {os.path.basename(pdf_file)} - {e}")
#             continue

#     print(f"\n[info] 批量处理完成:")
#     print(f"  成功: {success_count} 个文件")
#     print(f"  失败: {error_count} 个文件")
#     print(f"  总计: {len(pdf_files)} 个文件")


# if __name__ == "__main__":
#     if len(sys.argv) < 3:
#         print("Usage:")
#         print("  单个文件: python embed_and_ingest_chunks.py <pdf_path> <config.json>")
#         print("  批量文件夹: python embed_and_ingest_chunks.py --folder <folder_path> <config.json>")
#         sys.exit(1)
    
#     with open(sys.argv[-1], "r", encoding="utf-8") as f:
#         cfg = json.load(f)
    
#     if len(sys.argv) == 4 and sys.argv[1] == "--folder":
#         # 批量模式
#         folder_path = sys.argv[2]
#         ingest_folder_batch(folder_path, cfg)
#     else:
#         # 单文件模式
#         pdf_path = sys.argv[1]
#         ingest_pdf_single_index(pdf_path, cfg)
