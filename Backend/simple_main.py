# -*- coding: utf-8 -*-
"""
简化的FastAPI服务器 - 只包含基本的搜索功能
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import json
import uvicorn

# 导入现有的混合搜索功能
import sys
sys.path.append(os.path.dirname(__file__))
from hybrid_query import hybrid_query_top3

# 创建FastAPI应用
app = FastAPI(
    title="IDU-RAG Backend API",
    description="RAG系统后端API，提供混合搜索功能",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Pydantic模型
class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="搜索查询文本")
    alpha: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    kvec: Optional[int] = Field(default=10, ge=1, le=50)
    kbm25: Optional[int] = Field(default=10, ge=1, le=50)
    top_n: Optional[int] = Field(default=3, ge=1, le=50)

class SearchResponse(BaseModel):
    ok: bool
    query: str
    results: List[Dict[str, Any]]

# 基本路由
@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "IDU-RAG Backend API is running",
        "version": "1.0.0",
        "status": "healthy",
        "available_routes": [
            "/api/search/hybrid",
            "/docs"
        ]
    }

# 混合搜索接口
@app.post("/api/search/hybrid", response_model=SearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """混合搜索接口（向量 + BM25）"""
    try:
        # 检查配置文件
        if not os.path.exists(CONFIG_PATH):
            raise HTTPException(status_code=500, detail="配置文件不存在")
        
        # 加载配置
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        # 调用混合查询功能
        results = hybrid_query_top3(
            query_text=request.query,
            cfg=cfg,
            k_vec=request.kvec,
            k_bm25=request.kbm25,
            alpha=request.alpha
        )
        
        return SearchResponse(
            ok=True,
            query=request.query,
            results=results[:request.top_n]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

# 健康检查接口
@app.get("/api/health")
async def health_check():
    """详细健康检查"""
    try:
        config_exists = os.path.exists(CONFIG_PATH)
        
        return {
            "status": "healthy",
            "config_file": config_exists,
            "config_path": CONFIG_PATH,
            "api_version": "1.0.0"
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 启动IDU-RAG Backend API服务器...")
    print(f"📁 配置文件路径: {CONFIG_PATH}")
    print("🌐 服务地址: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("🔍 搜索接口: http://localhost:8000/api/search/hybrid")
    
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./"]
    )