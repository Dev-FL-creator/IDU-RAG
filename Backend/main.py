"""
FastAPI 主服务器 - 整合所有路由供Frontend调用
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import uvicorn


# 导入所有路由
from routers.query_routes import router as query_router
from routers.pdf_ingest_routes import router as pdf_router
from routers.chat_routes import router as chat_router
from routers.project_routes import router as project_router

# 创建FastAPI应用
app = FastAPI(
    title="IDU-RAG Backend API",
    description="RAG系统后端API，提供PDF处理、向量搜索和混合查询功能",
    version="1.0.0"
)

# 配置CORS，允许Frontend跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册所有路由
app.include_router(query_router)
app.include_router(pdf_router)
app.include_router(chat_router)
app.include_router(project_router)

# ========== 基本路由 ==========

@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "message": "IDU-RAG Backend API is running",
        "version": "1.0.0",
        "status": "healthy",
        "available_routes": [
            "/api/search/hybrid",
            "/api/search/hybrid_batch", 
            "/api/search/health",
            "/api/upload_pdfs",
            "/api/progress/{job_id}",
            "/docs"
        ]
    }

if __name__ == "__main__":
    print("启动IDU-RAG Backend API服务器...")
    print("服务地址: http://localhost:8001")
    print("API文档: http://localhost:8001/docs")
    print("搜索接口: http://localhost:8001/api/search/hybrid")
    print("PDF上传: http://localhost:8001/api/upload_pdfs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["./"]
    )