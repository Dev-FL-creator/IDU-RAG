# Azure OpenAI 和 AI Search PDF 处理系统 - 模块化版本

这个项目将Azure OpenAI和AI Search的功能分解成三个独立的模块：
1. **创建索引** - 使用`create_index_routes.py`
2. **处理PDF和上传嵌入** - 使用`upload_embedding_routes.py`
3. **执行查询** - 使用`query_routes.py`

每个脚本都是独立的，可以单独运行，并使用共同的JSON配置文件。

## 文件说明
Deepseek Api
https://platform.deepseek.com/api_keys
- `create_index_routes.py` - 创建Azure AI Search索引
- `upload_embedding_routes.py` - 处理PDF文件并上传嵌入向量
- `query_routes.py` - 执行查询并返回结果
- `config.json` - 通用配置文件模板
- `project_config.json` - 根据项目配置生成的特定配置文件

## 安装依赖

```bash
pip install azure-search-documents openai PyPDF2 requests
```

## 配置文件说明

配置文件 (config.json) 包含所有需要的参数：


## 使用方法
激活环境
```bash
Backend\azure_openai_env\Scripts\activate
```

### 第1步：创建索引

```bash
python create_index.py [配置文件路径]
python Backend/create_index.py "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Backend\config.json"
```

如果不提供配置文件路径，将默认使用当前目录下的 `config.json`。

### 第2步：上传PDF并生成嵌入

处理单个PDF文件：

```bash
python Backend/embed_and_ingest_chunks.py "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\test_pdf.pdf" "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Backend\config.json"
```

批量处理文档下所有pdf文件：
```bash
python Backend/embed_and_ingest_chunks.py --folder "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Test Data\Institute VB\ACC Equipments" "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Backend\config.json" 
```

### 第3步：执行查询
“We are looking for partners with experience in microstructure or material simulation projects similar to ours. What collaborations or capabilities does this company offer?”

“Our team is interested in joint R&D on microstructure modeling and material forming — are there any similar projects mentioned in your database?”

“Which organizations have expertise in structure or process simulation that could be potential collaboration partners?”

“We would like to collaborate on metal forming or structure simulation projects. Which company profiles in your index mention such capabilities?”


kvec:向量搜索的top k
kbm25:BM25的top k
alpha:语义贡献比重
```bash
python Backend/hybrid_query.py `
"Which organizations have expertise in structure or process simulation that could be potential collaboration partners?" `
"C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Backend\config.json" `
--kvec 10 --kbm25 10 --alpha 0.7
```

参数说明：
- `查询文本` - 必需，要查询的文本
- `配置文件路径` - 可选，默认为当前目录下的`config.json`
- `结果数量` - 可选，要返回的结果数量，默认为3

## 工作流程示例

下面是一个完整的工作流程示例：

```bash
# 步骤1：创建索引
python create_index.py project_config.json

# 步骤2：处理PDF文件
python upload_embedding_routes.py ./pdf_files project_config.json

# 步骤3：执行查询
python query_routes.py "这些文档主要讨论了什么内容？" project_config.json 5
```

## 每个脚本的详细功能

### 1. create_index_routes.py

- 读取JSON配置文件
- 检查索引是否已存在
- 创建具有向量搜索功能的新索引
- 定义索引字段（id、content、filepath、content_vector）

### 2. upload_embedding_routes.py

- 从PDF文件中提取文本
- 将文本分割成合适大小的块
- 为每个文本块生成嵌入向量
- 将文档和向量上传到Azure AI Search索引
- 支持处理单个PDF文件或整个目录

### 3. query_routes.py

- 为查询文本生成嵌入向量
- 使用向量搜索在索引中查找相关内容
- 使用Azure OpenAI根据找到的内容生成回答
- 返回回答和来源信息

## 注意事项

- 确保所有API密钥和端点配置正确
- 针对大型PDF文件，程序会自动分块处理以优化索引和查询性能
- 使用`project_config.json`作为你项目的配置文件，它包含了项目特定的配置信息
