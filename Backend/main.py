"""
FastAPI Main Server - Integrates all routes for Frontend

Routes:
- /auth/* - User authentication (register, login)
- /projects/* - Project management (CRUD)
- /conversations/* - Conversation management (CRUD, messages)
- /api/search/* - Search functionality
- /api/upload_pdfs - PDF upload and processing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import routes
from routers.query_routes import router as query_router
from routers.pdf_ingest_routes import router as pdf_router
from routers.user_routes import router as user_router
from routers.project_routes import router as project_router
from routers.chat_routes import router as chat_router

# Create FastAPI app
app = FastAPI(
    title="IDU-RAG Backend API",
    description="RAG Backend API with user authentication, project management, and chat functionality",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(user_router, tags=["Authentication"])
app.include_router(project_router, tags=["Projects"])
app.include_router(chat_router, tags=["Conversations"])
app.include_router(query_router, tags=["Search"])
app.include_router(pdf_router, tags=["PDF"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "IDU-RAG Backend API is running",
        "version": "2.0.0",
        "status": "healthy",
        "available_routes": {
            "auth": [
                "POST /auth/register - Register new user",
                "POST /auth/login - Login user",
                "GET /auth/user/{user_id} - Get user info"
            ],
            "projects": [
                "GET /projects - List projects",
                "POST /projects - Create project",
                "GET /projects/{id} - Get project",
                "PUT /projects/{id} - Update project",
                "DELETE /projects/{id} - Delete project"
            ],
            "conversations": [
                "GET /conversations - List conversations",
                "POST /conversations - Create conversation",
                "GET /conversations/{id} - Get conversation with messages",
                "PUT /conversations/{id} - Update conversation",
                "DELETE /conversations/{id} - Delete conversation",
                "POST /conversations/{id}/move - Move to project",
                "POST /conversations/{id}/messages - Add message"
            ],
            "search": [
                "POST /api/search/hybrid - Hybrid search",
                "GET /api/search/health - Search health check"
            ],
            "pdf": [
                "POST /api/upload_pdfs - Upload PDFs",
                "GET /api/progress/{job_id} - Get upload progress"
            ],
            "docs": "/docs - API documentation"
        }
    }


if __name__ == "__main__":
    print("Starting IDU-RAG Backend API server...")
    print("Server: http://localhost:8001")
    print("API Docs: http://localhost:8001/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["./"]
    )
