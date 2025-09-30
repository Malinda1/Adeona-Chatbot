# Define API routes here



from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime

from backend.app.core.chatbot import adeona_chatbot
from backend.app.models.chat_models import ChatMessage, ChatResponse
from backend.app.services.airtable_service import airtable_service
from backend.app.services.vectordb_service import vectordb_service
from backend.app.services.googlesheet_service import googlesheet_service
from backend.app.services.serpapi_service import serpapi_service
from backend.app.services.local_data_loader import local_data_loader
from backend.app.utils.logger import logger, log_function_call, log_error

# Create router instance
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: dict

@router.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Enhanced Adeona Technologies Chatbot API with Permanent Local Data Storage",
        "version": "2.0.0",
        "status": "active",
        "features": ["Local Data VectorDB", "SerpAPI Fallback", "Smart Routing"],
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """health check endpoint"""
    try:
        log_function_call("health_check")
        
        # Check service statuses
        services_status = {
            "vectordb": "unknown",
            "local_data_loader": "unknown",
            "airtable": "unknown", 
            "googlesheets": "unknown",
            "gemini": "active",
            "serpapi": "unknown"
        }
        
        # Test VectorDB
        try:
            stats = await vectordb_service.get_comprehensive_stats()
            services_status["vectordb"] = "active" if stats.get("total_vectors", 0) >= 0 else "error"
        except:
            services_status["vectordb"] = "error"
        
        # Test Local Data Loader
        try:
            data_info = await local_data_loader.check_data_freshness()
            services_status["local_data_loader"] = "active" if data_info.get("files_found", 0) > 0 else "no_data"
        except:
            services_status["local_data_loader"] = "error"
        
        # Test Airtable
        try:
            await airtable_service.get_customer_stats()
            services_status["airtable"] = "active"
        except:
            services_status["airtable"] = "error"
        
        # Test Google Sheets
        try:
            await googlesheet_service.ensure_initialized()
            services_status["googlesheets"] = "active"
        except:
            services_status["googlesheets"] = "error"
        
        # Test SerpAPI
        try:
            test_result = await serpapi_service.test_connection()
            services_status["serpapi"] = "active" if test_result["success"] else "error"
        except:
            services_status["serpapi"] = "error"
        
        overall_status = "healthy" if all(status in ["active", "unknown"] for status in services_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            services=services_status
        )
        
    except Exception as e:
        log_error(e, "health_check")
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            services={"error": str(e)}
        )

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """hat endpoint with permanent local data integration"""
    try:
        log_function_call("chat_endpoint", {"message_length": len(request.message)})
        
        # Create chat message
        chat_message = ChatMessage(
            message=request.message,
            session_id=request.session_id
        )
        
        # Process message with enhanced capabilities
        response = await adeona_chatbot.process_message(chat_message)
        
        logger.info(f"Chat response generated for session: {response.session_id}")
        return response
        
    except Exception as e:
        log_error(e, "chat_endpoint")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/audio/{filename}", tags=["Audio"])
async def get_audio_file(filename: str):
    """ Serve audio files with proper validation and security"""
    try:
        log_function_call("get_audio_file", {"filename": filename})
        
        # Validate filename to prevent directory traversal attacks
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            logger.warning(f"Invalid filename requested: {filename}")
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Only allow .wav files
        if not filename.endswith('.wav'):
            logger.warning(f"Non-WAV file requested: {filename}")
            raise HTTPException(status_code=400, detail="Only WAV files are supported")
        
        # Construct full file path
        file_path = os.path.join("static", "audio", filename)
        
        # Normalize the path to prevent issues
        file_path = os.path.normpath(file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"Audio file not found: {file_path}")
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            logger.warning(f"Requested path is not a file: {file_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Get file size for logging
        file_size = os.path.getsize(file_path)
        logger.info(f"Serving audio file: {file_path} ({file_size} bytes)")
        
        # Return file with proper headers
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=filename,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
            
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        log_error(e, "get_audio_file")
        logger.error(f"Unexpected error serving audio file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving audio file")

@router.get("/stats", tags=["Statistics"])
async def get_comprehensive_stats():
    """Get comprehensive chatbot and system statistics"""
    try:
        log_function_call("get_comprehensive_stats")
        
        # Get chatbot stats
        chatbot_stats = adeona_chatbot.get_session_stats()
        
        # Get customer stats
        customer_stats = await airtable_service.get_customer_stats()
        
        # Get comprehensive vector DB stats
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        
        # Get local data stats
        local_data_stats = await local_data_loader.check_data_freshness()
        
        # Get SerpAPI stats
        serpapi_test = await serpapi_service.test_connection()
        
        #  Add audio directory stats
        audio_stats = {
            "audio_files_count": 0,
            "total_audio_size": 0,
            "audio_directory_exists": False
        }
        
        try:
            audio_dir = "static/audio"
            if os.path.exists(audio_dir) and os.path.isdir(audio_dir):
                audio_stats["audio_directory_exists"] = True
                audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
                audio_stats["audio_files_count"] = len(audio_files)
                audio_stats["total_audio_size"] = sum(
                    os.path.getsize(os.path.join(audio_dir, f)) for f in audio_files
                )
        except Exception as e:
            logger.warning(f"Could not get audio stats: {e}")
        
        return {
            "chatbot": chatbot_stats,
            "customers": customer_stats,
            "vectordb": vectordb_stats,
            "local_data": local_data_stats,
            "audio": audio_stats,  # Include audio statistics
            "serpapi": {
                "available": serpapi_test["success"],
                "status": serpapi_test.get("api_status", "unknown")
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_comprehensive_stats")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

#  Add debug endpoint for audio testing
@router.get("/debug/audio", tags=["Debug"])
async def debug_audio_directory():
    """Debug endpoint to check audio directory status"""
    try:
        log_function_call("debug_audio_directory")
        
        audio_dir = "static/audio"
        debug_info = {
            "audio_directory": audio_dir,
            "directory_exists": os.path.exists(audio_dir),
            "is_directory": os.path.isdir(audio_dir) if os.path.exists(audio_dir) else False,
            "files": [],
            "total_files": 0,
            "total_size": 0
        }
        
        if os.path.exists(audio_dir) and os.path.isdir(audio_dir):
            try:
                all_files = os.listdir(audio_dir)
                wav_files = [f for f in all_files if f.endswith('.wav')]
                
                debug_info["files"] = []
                total_size = 0
                
                for filename in wav_files[-10:]:  # Show last 10 files
                    filepath = os.path.join(audio_dir, filename)
                    try:
                        size = os.path.getsize(filepath)
                        mtime = os.path.getmtime(filepath)
                        debug_info["files"].append({
                            "name": filename,
                            "size": size,
                            "modified": datetime.fromtimestamp(mtime).isoformat()
                        })
                        total_size += size
                    except Exception as e:
                        debug_info["files"].append({
                            "name": filename,
                            "error": str(e)
                        })
                
                debug_info["total_files"] = len(wav_files)
                debug_info["total_size"] = sum(
                    os.path.getsize(os.path.join(audio_dir, f)) 
                    for f in wav_files
                    if os.path.exists(os.path.join(audio_dir, f))
                )
                
            except Exception as e:
                debug_info["error"] = f"Error reading directory: {str(e)}"
        
        return debug_info
        
    except Exception as e:
        log_error(e, "debug_audio_directory")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

# Local Data Management Routes
@router.get("/admin/local-data/status", tags=["Admin - Local Data"])
async def get_local_data_status():
    """Get status of local scraped data files"""
    try:
        log_function_call("get_local_data_status")
        
        data_info = await local_data_loader.check_data_freshness()
        vectordb_stats = await vectordb_service.get_comprehensive_stats()
        
        return {
            "local_files": data_info,
            "vectordb_storage": {
                "local_data_vectors": vectordb_stats.get("local_data_vectors", 0),
                "total_vectors": vectordb_stats.get("total_vectors", 0),
                "data_loaded": vectordb_stats.get("local_data_loaded", False)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_local_data_status")
        raise HTTPException(status_code=500, detail=f"Error checking local data status: {str(e)}")

@router.post("/admin/local-data/reload", tags=["Admin - Local Data"])
async def reload_local_data():
    """Force reload of local scraped data into VectorDB"""
    try:
        log_function_call("reload_local_data")
        
        logger.info("Starting local data reload...")
        success = await vectordb_service.reload_local_data()
        
        if success:
            stats = await vectordb_service.get_comprehensive_stats()
            return {
                "message": "Local data successfully reloaded into VectorDB",
                "success": True,
                "local_vectors": stats.get("local_data_vectors", 0),
                "total_vectors": stats.get("total_vectors", 0),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "message": "Local data reload failed - check logs for details",
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        log_error(e, "reload_local_data")
        raise HTTPException(status_code=500, detail=f"Error during local data reload: {str(e)}")

@router.get("/admin/local-data/preview/{file_index}", tags=["Admin - Local Data"])
async def preview_local_file(file_index: int):
    """Preview content of a specific local data file"""
    try:
        log_function_call("preview_local_file", {"file_index": file_index})
        
        files = local_data_loader.find_scraped_files()
        
        if file_index < 0 or file_index >= len(files):
            raise HTTPException(status_code=404, detail="File index out of range")
        
        file_path = files[file_index]
        preview_content = local_data_loader.get_file_preview(file_path, max_chars=1000)
        
        return {
            "file_path": file_path,
            "file_index": file_index,
            "preview": preview_content,
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "preview_local_file")
        raise HTTPException(status_code=500, detail=f"Error previewing file: {str(e)}")

# Search Testing Routes
@router.get("/admin/test-search", tags=["Admin - Testing"])
async def test_enhanced_search(query: str = "privacy policy"):
    """Test enhanced search functionality with local data + SerpAPI fallback"""
    try:
        log_function_call("test_enhanced_search", {"query": query})
        
        # Test local data search
        local_results = await vectordb_service.search_adeona_knowledge(query, top_k=5, include_serpapi=False)
        
        # Test search with SerpAPI fallback
        fallback_results, used_fallback = await vectordb_service.search_with_fallback(query, top_k=8)
        
        # Test SerpAPI directly
        serpapi_results = await serpapi_service.search_adeona_specific(query, max_results=3)
        
        return {
            "query": query,
            "local_only_results": {
                "count": len(local_results),
                "results": [
                    {
                        "content_preview": result.content[:150] + "..." if len(result.content) > 150 else result.content,
                        "score": result.score,
                        "page_type": result.metadata.get("page_type", "unknown"),
                        "source": result.metadata.get("data_source", "unknown")
                    }
                    for result in local_results
                ]
            },
            "fallback_search": {
                "count": len(fallback_results),
                "used_serpapi_fallback": used_fallback,
                "results": [
                    {
                        "content_preview": result.content[:150] + "..." if len(result.content) > 150 else result.content,
                        "score": result.score,
                        "page_type": result.metadata.get("page_type", "unknown"),
                        "source": result.metadata.get("data_source", "unknown")
                    }
                    for result in fallback_results[:5]
                ]
            },
            "serpapi_direct": {
                "count": len(serpapi_results),
                "results": [
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", "")[:150] + "..." if len(result.get("snippet", "")) > 150 else result.get("snippet", ""),
                        "link": result.get("link", ""),
                        "relevance_score": result.get("relevance_score", 0)
                    }
                    for result in serpapi_results
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "test_enhanced_search")
        raise HTTPException(status_code=500, detail=f"Error during search test: {str(e)}")

@router.get("/admin/test-privacy-search", tags=["Admin - Testing"])
async def test_privacy_search():
    """Test privacy policy search functionality"""
    try:
        log_function_call("test_privacy_search")
        
        test_queries = [
            "privacy policy",
            "data protection", 
            "personal information",
            "data security",
            "privacy practices"
        ]
        
        results = {}
        
        for query in test_queries:
            # Test local VectorDB privacy search
            local_privacy_results = await vectordb_service.search_privacy_policy(query)
            
            # Test SerpAPI privacy search
            serpapi_privacy_results = await serpapi_service.search_privacy_policy(query)
            
            results[query] = {
                "local_results": {
                    "count": len(local_privacy_results),
                    "best_score": local_privacy_results[0].score if local_privacy_results else 0,
                    "preview": local_privacy_results[0].content[:100] + "..." if local_privacy_results else "No content"
                },
                "serpapi_results": {
                    "count": len(serpapi_privacy_results),
                    "best_score": serpapi_privacy_results[0].get("relevance_score", 0) if serpapi_privacy_results else 0,
                    "preview": serpapi_privacy_results[0].get("snippet", "")[:100] + "..." if serpapi_privacy_results else "No content"
                }
            }
        
        return {
            "test_results": results,
            "timestamp": datetime.now().isoformat(),
            "recommendation": "Local data should provide the primary results, SerpAPI as fallback"
        }
        
    except Exception as e:
        log_error(e, "test_privacy_search")
        raise HTTPException(status_code=500, detail=f"Error during privacy search test: {str(e)}")

# Legacy compatibility routes
@router.post("/admin/reindex", tags=["Admin - Legacy"])
async def legacy_reindex(background_tasks: BackgroundTasks):
    """Legacy reindex endpoint - now uses local data reload"""
    try:
        background_tasks.add_task(local_data_reload_task)
        return {
            "message": "Local data reload started in background",
            "timestamp": datetime.now().isoformat(),
            "method": "Enhanced Local Data Storage"
        }
    except Exception as e:
        log_error(e, "legacy_reindex")
        raise HTTPException(status_code=500, detail="Error starting data reload")

@router.post("/admin/cleanup", tags=["Admin"])
async def cleanup_sessions():
    """Clean up old chat sessions (admin function)"""
    try:
        log_function_call("cleanup_sessions")
        
        adeona_chatbot.cleanup_old_sessions(hours=24)
        
        return {
            "message": "Session cleanup completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "cleanup_sessions")
        raise HTTPException(status_code=500, detail="Error during session cleanup")

@router.get("/contact", tags=["Contact"])
async def get_contact_info():
    """Get contact information"""
    try:
        log_function_call("get_contact_info")
        
        contact_info = await googlesheet_service.get_all_contact_info()
        
        contact_dict = {}
        for contact in contact_info:
            contact_dict[contact.source_name] = contact.source
        
        return {
            "contact_info": contact_dict,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_contact_info")
        raise HTTPException(status_code=500, detail="Error retrieving contact information")

@router.get("/services", tags=["Services"])
async def get_services():
    """Get company services information"""
    try:
        log_function_call("get_services")
        
        from backend.app.config.settings import settings
        
        return {
            "services": settings.COMPANY_SERVICES,
            "services_by_category": settings.SERVICE_CATEGORIES,
            "website": settings.WEBSITE_URL,
            "phone": settings.CONTACT_INFO["phone"],
            "email": settings.CONTACT_INFO["email"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_services")
        raise HTTPException(status_code=500, detail="Error retrieving services information")

# Background task functions
async def local_data_reload_task():
    """Background task for reloading local data"""
    try:
        logger.info("Starting background local data reload...")
        
        success = await vectordb_service.reload_local_data()
        
        if success:
            logger.info("Background local data reload completed successfully")
        else:
            logger.error("Background local data reload failed")
            
    except Exception as e:
        log_error(e, "local_data_reload_task")

