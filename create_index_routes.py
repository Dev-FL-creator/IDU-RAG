import os
import json
import sys
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    SearchFieldDataType
)

def create_index_from_config(config_path):
    # 加载配置
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    
    # 初始化索引客户端
    search_endpoint = f"https://{config['search_service_name']}.search.windows.net"
    search_index_client = SearchIndexClient(
        endpoint=search_endpoint,
        credential=AzureKeyCredential(config["search_api_key"])
    )
    
    index_name = config["index_name"]
    embedding_dimensions = config.get("embedding_dimensions", 1536)
    
    # 检查索引是否已存在
    if index_name in [index.name for index in search_index_client.list_indexes()]:
        print(f"索引 {index_name} 已存在")
        return
    
    # 定义向量搜索配置 - 使用字典而不是特定类
    vector_search = {
        "algorithms": [
            {
                "name": "my-hnsw-config", 
                "kind": "hnsw",
                "parameters": {
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": config.get("vector_metric", "cosine")
                }
            }
        ],
        "profiles": [
            {
                "name": "my-vector-profile",
                "algorithm": "my-hnsw-config"
            }
        ]
    }
    
    # 定义索引字段
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="filepath", type=SearchFieldDataType.String),
        # 向量字段定义
        {
            "name": "content_vector",
            "type": SearchFieldDataType.Collection(SearchFieldDataType.Single),
            "searchable": False,
            "filterable": False,
            "sortable": False,
            "facetable": False,
            "dimensions": embedding_dimensions,
            "vectorSearchProfile": "my-vector-profile"
        }
    ]
    
    # 创建索引
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    search_index_client.create_index(index)
    print(f"已成功创建索引: {index_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.json"
    
    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)
    
    create_index_from_config(config_path)