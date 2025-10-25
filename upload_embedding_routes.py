import os
import json
import sys
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """从PDF文件中提取文本"""
    text = ""
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
            
    return text

def chunk_text(text, max_chunk_size=5000, overlap=200):
    """将文本分割成带有重叠的块"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        if end < len(text) and end - start == max_chunk_size:
            # 尝试找到一个好的断点（如换行符或句号）
            break_point = text.rfind("\n", start, end)
            if break_point == -1 or end - break_point > 1000:
                break_point = text.rfind(". ", start, end)
            if break_point != -1 and end - break_point < 1000:
                end = break_point + 1
        
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    
    return chunks

def generate_embedding(text, openai_client, model):
    """使用Azure OpenAI生成嵌入向量"""
    response = openai_client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

def upload_embeddings_from_pdf(pdf_path, config_path):
    """从PDF文件中提取文本，生成嵌入向量，并上传到Azure AI Search"""
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
    
    # 从PDF提取文本
    print(f"从PDF文件提取文本: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    
    # 使用文件名作为文档ID
    filename = os.path.basename(pdf_path)
    
    # 分块文本
    chunks = chunk_text(text)
    print(f"文本已分割成 {len(chunks)} 个块")
    
    # 处理并上传每个块
    documents = []
    for i, chunk in enumerate(chunks):
        print(f"处理块 {i+1}/{len(chunks)}")
        
        # 生成嵌入向量
        embedding = generate_embedding(chunk, openai_client, config["embedding_model"])
        
        # 创建文档
        doc = {
            "id": f"{filename}-{i}",
            "content": chunk,
            "filepath": pdf_path,
            "content_vector": embedding
        }
        
        documents.append(doc)
        
        # 每10个文档批量上传一次
        if len(documents) >= 10 or (i == len(chunks) - 1 and documents):
            search_client.upload_documents(documents)
            print(f"已上传 {len(documents)} 个文档到索引 {config['index_name']}")
            documents = []
    
    print(f"已完成PDF文件的处理和上传: {pdf_path}")

def process_pdf_directory(dir_path, config_path):
    """处理目录中的所有PDF文件"""
    if not os.path.isdir(dir_path):
        print(f"错误：{dir_path} 不是一个有效的目录")
        return
    
    pdf_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"警告：目录 {dir_path} 中没有找到PDF文件")
        return
    
    print(f"在目录 {dir_path} 中找到 {len(pdf_files)} 个PDF文件")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(dir_path, pdf_file)
        upload_embeddings_from_pdf(pdf_path, config_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python upload_embedding_routes.py <pdf文件或目录路径> [配置文件路径]")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if len(sys.argv) > 2:
        config_path = sys.argv[2]
    else:
        config_path = "config.json"
    
    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)
    
    if os.path.isdir(path):
        process_pdf_directory(path, config_path)
    elif os.path.isfile(path) and path.lower().endswith('.pdf'):
        upload_embeddings_from_pdf(path, config_path)
    else:
        print(f"错误：{path} 不是有效的PDF文件或目录")
        sys.exit(1)
