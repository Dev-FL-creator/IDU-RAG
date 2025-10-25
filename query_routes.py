import os
import json
import sys
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

def generate_embedding(text, openai_client, model):
    """使用Azure OpenAI生成嵌入向量"""
    response = openai_client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

def query_with_vector_search(query_text, config_path, top_k=3):
    """使用向量搜索和OpenAI查询索引"""
    # 加载配置
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    # 初始化Azure OpenAI客户端
    openai_client = AzureOpenAI(
        api_key=config["openai_api_key"],
        api_version=config["openai_api_version"],
        azure_endpoint=config["openai_endpoint"]
    )
    
    # 初始化搜索客户端
    search_endpoint = f"https://{config['search_service_name']}.search.windows.net"
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=config["index_name"],
        credential=AzureKeyCredential(config["search_api_key"])
    )
    
    # 为查询生成嵌入向量
    print(f"为查询文本生成嵌入向量: {query_text}")
    query_embedding = generate_embedding(query_text, openai_client, config["embedding_model"])
    
    # 执行向量搜索
    print(f"执行向量搜索，获取前 {top_k} 个结果...")
    results = search_client.search(
        search_text=None,
        vector={"vector": query_embedding, "fields": "content_vector", "k": top_k},
        select=["id", "content", "filepath"],
        top=top_k
    )
    
    # 收集结果
    documents = list(results)
    if not documents:
        print("没有找到相关文档")
        return {
            "answer": "抱歉，没有找到与您的查询相关的信息。",
            "sources": []
        }
    
    # 格式化结果作为上下文
    context = ""
    for i, doc in enumerate(documents):
        context += f"文档 {i+1}:\n{doc['content']}\n\n"
    
    # 使用OpenAI根据上下文回答查询
    print("使用OpenAI生成回答...")
    response = openai_client.chat.completions.create(
        model=config["openai_deployment"],
        messages=[
            {"role": "system", "content": "您是一个基于提供的上下文信息回答问题的助手。您只使用提供的上下文信息来回答问题，不使用任何其他知识。如果上下文中没有足够的信息来回答问题，您会说明您无法回答。"},
            {"role": "user", "content": f"以下是上下文信息：\n\n{context}\n\n根据上述信息，请回答以下问题：{query_text}"}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    
    answer = response.choices[0].message.content
    
    # 组装结果
    result = {
        "answer": answer,
        "sources": []
    }
    
    # 添加来源信息
    for doc in documents:
        result["sources"].append({
            "id": doc["id"],
            "filepath": doc["filepath"]
        })
    
    return result

def display_result(result):
    """格式化显示查询结果"""
    print("\n" + "=" * 50)
    print("查询回答:")
    print(result["answer"])
    print("\n" + "=" * 50)
    print("信息来源:")
    for i, source in enumerate(result["sources"]):
        print(f"{i+1}. {source['id']} - {source['filepath']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python query_routes.py <查询文本> [配置文件路径] [结果数量]")
        sys.exit(1)
    
    query_text = sys.argv[1]
    
    config_path = "config.json"
    if len(sys.argv) > 2:
        config_path = sys.argv[2]
    
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
    
    result = query_with_vector_search(query_text, config_path, top_k)
    display_result(result)
