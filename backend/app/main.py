# Entry point for FastAPI app

# Entry point for FastAPI app

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager

from backend.app.routes import router
from backend.app.core.chatbot import adeona_chatbot
from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error

# Create necessary directories before app initialization
os.makedirs("static/audio", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    try:
        logger.info("Starting Adeona Chatbot application...")
        
        # Validate settings
        settings.validate_settings()
        
        # Initialize chatbot services
        await adeona_chatbot.initialize_services()
        
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as e:
        log_error(e, "application_startup")
        raise e
    finally:
        logger.info("Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="Adeona Technologies Chatbot API",
    description="Advanced AI chatbot for Adeona Technologies customer service and information",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your deployment needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Try to mount frontend static files if they exist
frontend_static_path = "frontend/static"
if os.path.exists(frontend_static_path):
    app.mount("/frontend/static", StaticFiles(directory=frontend_static_path), name="frontend_static")

# Serve frontend files
@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    # Try multiple possible paths for the frontend
    possible_paths = [
        "frontend/index.html",
        "../frontend/index.html", 
        "./frontend/index.html",
        "index.html"
    ]
    
    for frontend_path in possible_paths:
        if os.path.exists(frontend_path):
            logger.info(f"Serving frontend from: {frontend_path}")
            return FileResponse(
                frontend_path,
                media_type="text/html",
                headers={"Cache-Control": "no-cache"}
            )
    
    # If no frontend file found, return JSON response
    logger.warning("Frontend HTML file not found in any expected location")
    return {
        "message": "Adeona Technologies Chatbot API is running",
        "status": "active",
        "api_docs": "/docs",
        "frontend_note": "Frontend HTML file not found - API only mode"
    }

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    possible_paths = [
        "frontend/static/assets/favicon.ico",
        "../frontend/static/assets/favicon.ico",
        "static/favicon.ico",
        "favicon.ico"
    ]
    
    for favicon_path in possible_paths:
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
    
    raise HTTPException(status_code=404, detail="Favicon not found")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    log_error(exc, f"Global exception for {request.url}")
    return HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint at root level
@app.get("/health")
async def root_health():
    """Root level health check"""
    return {"status": "healthy", "service": "Adeona Chatbot API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )