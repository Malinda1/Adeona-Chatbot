# Entry point for FastAPI app - UPDATED WITH CANCELLATION FIX

# Enhanced main application with local data integration and FIXED CANCELLATION

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from datetime import datetime
from contextlib import asynccontextmanager

from backend.app.routes import router
from backend.app.core.chatbot import adeona_chatbot
from backend.app.config.settings import settings
from backend.app.services.vectordb_service import vectordb_service
from backend.app.services.local_data_loader import local_data_loader
from backend.app.utils.logger import logger, log_error

# Create necessary directories before app initialization
os.makedirs("static/audio", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Enhanced lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifespan events with permanent local data loading and cancellation support"""
    try:
        logger.info("Starting Enhanced Adeona Chatbot with Permanent Local Data Storage and Fixed Cancellation...")
        
        # Validate settings
        settings.validate_settings()
        logger.info("✓ Settings validated")
        
        # Check local data availability
        data_info = await local_data_loader.check_data_freshness()
        logger.info(f"✓ Local data files found: {data_info.get('files_found', 0)}")
        
        if data_info.get('files_found', 0) == 0:
            logger.warning("⚠ No local scraped data files found - chatbot will rely on basic knowledge + SerpAPI")
        else:
            logger.info(f"✓ Local data available: {data_info.get('total_files_size', 0)} bytes total")
        
        # Initialize services (VectorDB will automatically load local data permanently)
        logger.info("Initializing services...")
        await adeona_chatbot.initialize_services()
        
        # Verify VectorDB initialization and local data loading
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        local_vectors = vectordb_stats.get('local_data_vectors', 0)
        total_vectors = vectordb_stats.get('total_vectors', 0)
        
        if local_vectors > 0:
            logger.info(f"✓ Local data permanently loaded: {local_vectors} vectors in VectorDB")
        else:
            logger.warning("⚠ No local data vectors found - may need to reload local data")
        
        logger.info(f"✓ Total VectorDB vectors: {total_vectors}")
        
        # Log system capabilities including cancellation fix
        logger.info("System Capabilities:")
        logger.info(f"  • Local Data Storage: {'✓ Active' if local_vectors > 0 else '✗ No Data'}")
        logger.info(f"  • SerpAPI Fallback: {'✓ Available' if settings.SERPAPI_API_KEY else '✗ Not Configured'}")
        logger.info(f"  • Service Booking: ✓ Active")
        logger.info(f"  • Service Cancellation: ✓ Fixed & Active (24-hour window)")
        logger.info(f"  • Audio Responses: ✓ Active")
        
        logger.info("🚀 Enhanced Adeona Chatbot with Fixed Cancellation startup completed successfully!")
        
        yield
        
    except Exception as e:
        log_error(e, "application_startup")
        logger.error("❌ Application startup failed!")
        raise e
    finally:
        logger.info("Application shutdown completed")

# Create enhanced FastAPI application
app = FastAPI(
    title="Enhanced Adeona Technologies Chatbot API",
    description="Advanced AI chatbot with permanent local data storage, intelligent search, real-time fallback capabilities, and FIXED service cancellation within 24-hour window",
    version="2.1.0",  # Updated version to reflect cancellation fix
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your deployment needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include enhanced routes
app.include_router(router, prefix="/api/v1")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Try to mount frontend static files if they exist
frontend_static_path = "frontend/static"
if os.path.exists(frontend_static_path):
    app.mount("/frontend/static", StaticFiles(directory=frontend_static_path), name="frontend_static")

# Enhanced frontend serving
@app.get("/")
async def serve_frontend():
    """Serve the main frontend page with enhanced capabilities info including cancellation fix"""
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
    
    # Enhanced API-only response with system status including cancellation
    try:
        # Get quick system status
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        data_info = await local_data_loader.check_data_freshness()
        
        return {
            "message": "Enhanced Adeona Technologies Chatbot API with Fixed Cancellation",
            "version": "2.1.0",
            "status": "active",
            "features": [
                "Permanent Local Data Storage",
                "Intelligent Vector Search",
                "SerpAPI Real-time Fallback",
                "Smart Query Routing",
                "Service Booking System",
                "FIXED Service Cancellation (24-hour window)",
                "Audio Response Generation"
            ],
            "system_status": {
                "local_data_files": data_info.get("files_found", 0),
                "vectordb_vectors": vectordb_stats.get("total_vectors", 0),
                "local_data_vectors": vectordb_stats.get("local_data_vectors", 0),
                "serpapi_available": bool(settings.SERPAPI_API_KEY),
                "cancellation_system": "active"  # Added cancellation status
            },
            "cancellation_policy": {
                "enabled": True,
                "time_window": "24 hours",
                "requires_user_id": True,
                "contact_after_window": "(+94) 117 433 3333"
            },
            "api_endpoints": {
                "chat": "/api/v1/chat",
                "health": "/api/v1/health",
                "stats": "/api/v1/stats",
                "docs": "/docs",
                "admin": "/api/v1/admin/"
            },
            "frontend_note": "Frontend HTML file not found - API only mode"
        }
        
    except Exception as e:
        log_error(e, "serve_frontend")
        return {
            "message": "Enhanced Adeona Technologies Chatbot API with Fixed Cancellation",
            "version": "2.1.0",
            "status": "active",
            "api_docs": "/docs",
            "cancellation_system": "active",
            "error": "Could not load system status"
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

# Enhanced global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Enhanced global exception handler with better logging"""
    log_error(exc, f"Global exception for {request.url}")
    
    # Provide more helpful error messages based on the exception type
    if "vectordb" in str(exc).lower():
        detail = "Vector database error - please check system status"
    elif "serpapi" in str(exc).lower():
        detail = "Search service error - using fallback responses"
    elif "gemini" in str(exc).lower():
        detail = "AI service error - please try again"
    elif "airtable" in str(exc).lower():
        detail = "Database service error - cancellation may be affected"
    else:
        detail = "Internal server error - please contact support"
    
    return HTTPException(status_code=500, detail=detail)

# Enhanced health check endpoint at root level
@app.get("/health")
async def root_health():
    """Enhanced root level health check with system status including cancellation"""
    try:
        # Quick health indicators
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        
        return {
            "status": "healthy",
            "service": "Enhanced Adeona Chatbot API",
            "version": "2.1.0",
            "local_data_loaded": vectordb_stats.get("local_data_loaded", False),
            "total_vectors": vectordb_stats.get("total_vectors", 0),
            "cancellation_system": "active",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        log_error(e, "root_health")
        return {
            "status": "degraded",
            "service": "Enhanced Adeona Chatbot API",
            "error": str(e)
        }

# System information endpoint
@app.get("/system-info")
async def system_info():
    """Get comprehensive system information including cancellation feature status"""
    try:
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        data_info = await local_data_loader.check_data_freshness()
        
        return {
            "system": {
                "name": "Enhanced Adeona Technologies Chatbot",
                "version": "2.1.0",
                "mode": "Production with Permanent Local Data Storage and Fixed Cancellation"
            },
            "capabilities": {
                "local_data_storage": vectordb_stats.get("local_data_vectors", 0) > 0,
                "serpapi_fallback": bool(settings.SERPAPI_API_KEY),
                "service_booking": True,
                "service_cancellation": True,  # Now properly implemented
                "cancellation_time_window": "24 hours",
                "audio_responses": True,
                "smart_routing": True
            },
            "data_sources": {
                "local_files": data_info.get("files_found", 0),
                "local_vectors": vectordb_stats.get("local_data_vectors", 0),
                "serpapi_vectors": vectordb_stats.get("serpapi_vectors", 0),
                "total_vectors": vectordb_stats.get("total_vectors", 0)
            },
            "company_info": {
                "name": settings.COMPANY_INFO["name"],
                "website": settings.COMPANY_INFO["website"],
                "phone": settings.CONTACT_INFO["phone"],
                "email": settings.CONTACT_INFO["email"]
            },
            "cancellation_policy": {
                "enabled": True,
                "time_limit_hours": 24,
                "requires_user_id": True,
                "user_id_format": "8-character alphanumeric",
                "contact_after_limit": settings.CONTACT_INFO["phone"],
                "automatic_deletion": True
            }
        }
        
    except Exception as e:
        log_error(e, "system_info")
        return {
            "system": {
                "name": "Enhanced Adeona Technologies Chatbot",
                "version": "2.1.0",
                "status": "error"
            },
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )