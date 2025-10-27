import os
import json
import sys
from typing import List, Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI


def generate_embedding(text: str, openai_client: AzureOpenAI, deployment: str) -> List[float]:
    """Create query embedding with Azure OpenAI (deployment name)."""
    resp = openai_client.embeddings.create(
        input=text,
        model=deployment
    )
    return resp.data[0].embedding


def query_with_vector_search(query_text: str, config_path: str, top_k: int = 3) -> Dict[str, Any]:
    """Vector search over a single index where each document stores chunk text, vector, and structured fields."""
    # Load config
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Azure OpenAI client
    openai_client = AzureOpenAI(
        api_key=cfg["openai_api_key"],
        api_version=cfg["openai_api_version"],
        azure_endpoint=cfg["openai_endpoint"],
    )

    # Azure AI Search client
    search_client = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=cfg["index_name"],
        credential=AzureKeyCredential(cfg["search_api_key"]),
    )

    # Build query embedding
    print(f"为查询文本生成嵌入向量: {query_text}")
    query_embedding = generate_embedding(query_text, openai_client, cfg["embedding_model"])

    # Vector search — IMPORTANT: key must be 'value' for SDK 11.6.0
    print(f"执行向量搜索，获取前 {top_k} 个结果...")
    results = search_client.search(
        search_text=None,
        vector={"value": query_embedding, "fields": "content_vector", "k": top_k},
        # 把你关心的结构化字段一并取回
        select=[
            "id", "content", "filepath",
            "org_name", "country", "address", "founded_year", "size", "industry", "is_DU_member", "website",
            "members_name", "members_title", "members_role",
            "facilities_name", "facilities_type", "facilities_usage",
            "capabilities", "projects", "awards", "services",
            "contacts_name", "contacts_email", "contacts_phone",
            "addresses", "notes", "chunk_index", "source_id"
        ],
        top=top_k,
    )

    docs = list(results)
    if not docs:
        print("没有找到相关文档")
        return {"answer": "抱歉，没有找到与您的查询相关的信息。", "sources": []}

    # Assemble context: 每条命中包含结构化摘要 + 原文片段
    def fmt_list(v):
        if v is None: return ""
        if isinstance(v, list): return ", ".join(map(str, v))
        return str(v)

    context_parts = []
    for i, d in enumerate(docs, start=1):
        header = []
        if d.get("org_name"): header.append(f"Org: {d['org_name']}")
        if d.get("industry"): header.append(f"Industry: {d['industry']}")
        if d.get("capabilities"): header.append(f"Capabilities: {fmt_list(d['capabilities'])}")
        if d.get("contacts_email"): header.append(f"Emails: {fmt_list(d['contacts_email'])}")
        if d.get("website"): header.append(f"Website: {d['website']}")
        header_line = " | ".join(header) if header else "Org: (unknown)"

        ctx = (
            f"[DOC {i}] id={d['id']} | source_id={d.get('source_id')} | chunk_index={d.get('chunk_index')}\n"
            f"{header_line}\n"
            f"Content:\n{d.get('content','')}\n"
        )
        context_parts.append(ctx)

    context = "\n\n".join(context_parts)

    # Ask LLM to answer strictly based on provided context
    print("使用OpenAI生成回答...")
    chat_deployment = cfg["chat_model"]
    completion = openai_client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a grounded QA assistant. Answer ONLY using the provided context. "
                    "If the context is insufficient, say you don't know. "
                    "When possible, cite which [DOC i] your answer is based on."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {query_text}\n"
                    f"Instructions: Answer in Chinese. If useful, reference sources like [DOC 1], [DOC 2]."
                ),
            },
        ],
        temperature=0.2,
        max_tokens=800,
    )
    answer = completion.choices[0].message.content

    # Build sources list
    sources = []
    for d in docs:
        sources.append({
            "id": d["id"],
            "filepath": d.get("filepath"),
            "org_name": d.get("org_name"),
            "industry": d.get("industry"),
            "capabilities": d.get("capabilities"),
            "chunk_index": d.get("chunk_index"),
            "source_id": d.get("source_id"),
        })

    return {"answer": answer, "sources": sources}


def display_result(result: Dict[str, Any]) -> None:
    """Pretty print the final answer and sources."""
    print("\n" + "=" * 50)
    print("查询回答:")
    print(result["answer"])
    print("\n" + "=" * 50)
    print("信息来源:")
    for i, s in enumerate(result["sources"], start=1):
        cap = ", ".join(s["capabilities"] or []) if s.get("capabilities") else ""
        print(f"{i}. id={s['id']} | source_id={s.get('source_id')} | chunk={s.get('chunk_index')} | org={s.get('org_name')} | {s.get('filepath')} | {cap}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python query_routes.py <查询文本> [配置文件路径] [结果数量]")
        sys.exit(1)

    query_text = sys.argv[1]
    config_path = "config.json" if len(sys.argv) <= 2 else sys.argv[2]
    top_k = 3
    if len(sys.argv) > 3:
        try:
            top_k = int(sys.argv[3])
        except ValueError:
            print(f"警告: 无效的结果数量参数 '{sys.argv[3]}'，使用默认值 3")

    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)

    print(f"查询: {query_text}")
    print(f"使用配置文件: {config_path}")
    print(f"获取前 {top_k} 个结果")

    out = query_with_vector_search(query_text, config_path, top_k)
    display_result(out)
