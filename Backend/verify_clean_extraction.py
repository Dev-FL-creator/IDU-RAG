import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

def main():
    # 加载配置
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    
    # 创建搜索客户端
    search_client = SearchClient(
        endpoint=f"https://{cfg['search_service_name']}.search.windows.net",
        index_name=cfg["index_name"],
        credential=AzureKeyCredential(cfg["search_api_key"])
    )
    
    print("=== 验证重构后的DeepSeek智能提取效果 ===")
    
    # 获取最新的文档数据
    results = search_client.search(
        search_text="*",
        select="org_name,country,industry,capabilities,projects,services,contacts_name,members_name",
        top=3
    )
    
    for i, doc in enumerate(results, 1):
        print(f"\n 文档 {i}:")
        print(f"  组织名称: {doc.get('org_name')}")
        print(f"  国家: {doc.get('country')}")  
        print(f"  行业: {doc.get('industry')}")
        
        # 展示提取的内容数量
        capabilities = doc.get('capabilities', [])
        projects = doc.get('projects', [])
        services = doc.get('services', [])
        contacts = doc.get('contacts_name', [])
        members = doc.get('members_name', [])
        
        print(f"  能力数量: {len(capabilities)}")
        print(f"  项目数量: {len(projects)}")
        print(f"  服务数量: {len(services)}")
        print(f"  联系人数量: {len(contacts)}")
        print(f"  成员数量: {len(members)}")
        
        # 显示具体内容示例
        if capabilities:
            print(f"  主要能力: {capabilities[:3]}")
        if projects:
            print(f"  主要项目: {projects[:3]}")
    
    print("\n=== 数据质量评估 ===")
    
    # 检查字段填充率
    all_results = list(search_client.search(search_text="*", top=50))
    
    if all_results:
        sample = all_results[0]
        
        print(" 核心字段提取情况:")
        print(f"  组织名称: {'有效' if sample.get('org_name') else '空值'}")
        print(f"  国家: {'有效' if sample.get('country') else '空值'}")
        print(f"  行业: {'有效' if sample.get('industry') else '空值'}")
        
        print(" 数组字段提取情况:")
        print(f"  能力: {len(sample.get('capabilities', []))} 项")
        print(f"  项目: {len(sample.get('projects', []))} 项")
        print(f"  服务: {len(sample.get('services', []))} 项")
        
    
    print(f"\n 总计检查了 {len(all_results)} 个文档块")
    

if __name__ == "__main__":
    main()