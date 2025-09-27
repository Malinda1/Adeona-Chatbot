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
from backend.app.services.serpapi_service import serpapi_service  # Import new SerpAPI service
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
        "message": "Adeona Technologies Chatbot API",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        log_function_call("health_check")
        
        # Check service statuses
        services_status = {
            "vectordb": "unknown",
            "airtable": "unknown", 
            "googlesheets": "unknown",
            "gemini": "active",
            "serpapi": "unknown"
        }
        
        # Test VectorDB
        try:
            await vectordb_service.ensure_initialized()
            stats = await vectordb_service.get_index_stats()
            services_status["vectordb"] = "active" if stats.get("total_vector_count", 0) >= 0 else "error"
        except:
            services_status["vectordb"] = "error"
        
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
            if serpapi_service.serpapi_key:
                services_status["serpapi"] = "active"
            else:
                services_status["serpapi"] = "not_configured"
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
    """Main chat endpoint"""
    try:
        log_function_call("chat_endpoint", {"message_length": len(request.message)})
        
        # Create chat message
        chat_message = ChatMessage(
            message=request.message,
            session_id=request.session_id
        )
        
        # Process message
        response = await adeona_chatbot.process_message(chat_message)
        
        logger.info(f"Chat response generated for session: {response.session_id}")
        return response
        
    except Exception as e:
        log_error(e, "chat_endpoint")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/audio/{filename}", tags=["Audio"])
async def get_audio_file(filename: str):
    """Serve audio files"""
    try:
        file_path = f"static/audio/{filename}"
        
        if os.path.exists(file_path):
            return FileResponse(
                path=file_path,
                media_type="audio/wav",
                filename=filename
            )
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")
            
    except Exception as e:
        log_error(e, "get_audio_file")
        raise HTTPException(status_code=500, detail="Error serving audio file")

@router.get("/stats", tags=["Statistics"])
async def get_stats():
    """Get chatbot and system statistics"""
    try:
        log_function_call("get_stats")
        
        # Get chatbot stats
        chatbot_stats = adeona_chatbot.get_session_stats()
        
        # Get customer stats
        customer_stats = await airtable_service.get_customer_stats()
        
        # Get vector DB stats
        vectordb_stats = await vectordb_service.get_index_stats()
        
        return {
            "chatbot": chatbot_stats,
            "customers": customer_stats,
            "vectordb": vectordb_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_stats")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

@router.post("/admin/reindex", tags=["Admin"])
async def reindex_website(background_tasks: BackgroundTasks):
    """Reindex website content using SerpAPI (admin function) - FORCE COMPLETE REINDEX"""
    try:
        log_function_call("reindex_website")
        
        # Add reindexing to background tasks
        background_tasks.add_task(serpapi_reindex_content_task)
        
        return {
            "message": "FORCED website reindexing started in background using SerpAPI - all existing data will be replaced with comprehensive fresh content",
            "timestamp": datetime.now().isoformat(),
            "method": "SerpAPI enhanced extraction"
        }
        
    except Exception as e:
        log_error(e, "reindex_website")
        raise HTTPException(status_code=500, detail="Error starting reindex process")

@router.post("/admin/force-reindex", tags=["Admin"])
async def force_reindex_website():
    """Force immediate complete reindexing using SerpAPI (synchronous)"""
    try:
        log_function_call("force_reindex_website")
        
        logger.info("Starting immediate force reindex with SerpAPI...")
        success = await vectordb_service.force_reindex_website_content()
        
        if success:
            stats = await vectordb_service.get_index_stats()
            return {
                "message": "Website content successfully reindexed with comprehensive fresh data using SerpAPI",
                "success": True,
                "vector_count": stats.get('total_vector_count', 0),
                "timestamp": datetime.now().isoformat(),
                "method": "SerpAPI enhanced extraction"
            }
        else:
            return {
                "message": "Website reindexing failed - check logs for details",
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        log_error(e, "force_reindex_website")
        raise HTTPException(status_code=500, detail=f"Error during force reindex: {str(e)}")

@router.post("/admin/test-serpapi", tags=["Admin"])
async def test_serpapi_extraction():
    """Test SerpAPI content extraction (admin function)"""
    try:
        log_function_call("test_serpapi_extraction")
        
        logger.info("Testing SerpAPI content extraction...")
        
        # Test extraction from one page
        test_url = "https://adeonatech.net/privacy-policy"
        content = await serpapi_service.extract_page_content_via_serpapi(test_url)
        
        if content:
            return {
                "success": True,
                "message": "SerpAPI extraction test successful",
                "test_url": test_url,
                "content_length": len(content.content),
                "content_preview": content.content[:500] + "..." if len(content.content) > 500 else content.content,
                "page_type": content.page_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "SerpAPI extraction test failed - no content retrieved",
                "test_url": test_url,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        log_error(e, "test_serpapi_extraction")
        raise HTTPException(status_code=500, detail=f"Error during SerpAPI test: {str(e)}")

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

@router.get("/admin/vector-search-test", tags=["Admin"])
async def test_vector_search(query: str = "privacy policy"):
    """Test vector search functionality (admin function)"""
    try:
        log_function_call("test_vector_search", {"query": query})
        
        # Test general search
        general_results = await vectordb_service.search_similar(query, top_k=5)
        
        # Test privacy-specific search if query contains privacy terms
        privacy_results = []
        if "privacy" in query.lower():
            privacy_results = await vectordb_service.search_privacy_policy(query)
        
        return {
            "query": query,
            "general_results": [
                {
                    "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "score": result.score,
                    "page_type": result.metadata.get("page_type", "unknown"),
                    "url": result.metadata.get("url", "unknown")
                }
                for result in general_results
            ],
            "privacy_results": [
                {
                    "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "score": result.score,
                    "page_type": result.metadata.get("page_type", "unknown"),
                    "url": result.metadata.get("url", "unknown")
                }
                for result in privacy_results
            ],
            "general_count": len(general_results),
            "privacy_count": len(privacy_results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "test_vector_search")
        raise HTTPException(status_code=500, detail=f"Error during vector search test: {str(e)}")

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
            "contact_url": settings.CONTACT_URL,
            "phone": settings.PHONE_NUMBER,
            "email": settings.EMAIL,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        log_error(e, "get_services")
        raise HTTPException(status_code=500, detail="Error retrieving services information")

# Background task functions
async def reindex_content_task():
    """Background task for reindexing website content (legacy)"""
    try:
        logger.info("Starting background website content reindexing...")
        
        # Use the enhanced SerpAPI reindexing
        success = await vectordb_service.force_reindex_website_content()
        
        if success:
            logger.info("Background website reindexing completed successfully")
        else:
            logger.error("Background website reindexing failed")
            
    except Exception as e:
        log_error(e, "reindex_content_task")

async def serpapi_reindex_content_task():
    """Background task for FORCED reindexing of website content using SerpAPI"""
    try:
        logger.info("Starting FORCED background website content reindexing with SerpAPI...")
        
        # Force complete reindex using SerpAPI
        success = await vectordb_service.force_reindex_website_content()
        
        if success:
            stats = await vectordb_service.get_index_stats()
            logger.info(f"FORCED SerpAPI background reindexing completed successfully - {stats.get('total_vector_count', 0)} vectors indexed")
        else:
            logger.error("FORCED SerpAPI background reindexing failed")
            
    except Exception as e:
        log_error(e, "serpapi_reindex_content_task")
        
# Additional route for admin reindexing - Add this to your routes.py

@router.post("/admin/serpapi-reindex", tags=["Admin"])
async def force_serpapi_reindex():
    """Force immediate complete reindexing using SerpAPI only (synchronous)"""
    try:
        log_function_call("force_serpapi_reindex")
        
        logger.info("Starting immediate SERPAPI-ONLY reindex...")
        
        # Get current stats before reindexing
        old_stats = await vectordb_service.get_index_stats()
        old_count = old_stats.get('total_vector_count', 0)
        
        # Force reindex using SerpAPI only
        success = await vectordb_service.force_reindex_website_content()
        
        if success:
            # Get new stats after reindexing
            new_stats = await vectordb_service.get_index_stats()
            new_count = new_stats.get('total_vector_count', 0)
            
            # Test the reindexed content with privacy policy query
            test_privacy_results = await vectordb_service.search_privacy_policy("privacy policy data protection")
            test_general_results = await vectordb_service.search_similar("Adeona Technologies services", top_k=5)
            
            return {
                "message": "Website content successfully reindexed using SerpAPI ONLY",
                "success": True,
                "old_vector_count": old_count,
                "new_vector_count": new_count,
                "vectors_added": new_count - old_count,
                "privacy_test_results": len(test_privacy_results),
                "general_test_results": len(test_general_results),
                "extraction_method": "SerpAPI only - no web scraping",
                "timestamp": datetime.now().isoformat(),
                "test_queries": {
                    "privacy_policy_results": len(test_privacy_results),
                    "services_results": len(test_general_results)
                }
            }
        else:
            return {
                "message": "Website reindexing failed - check logs for details",
                "success": False,
                "extraction_method": "SerpAPI only",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        log_error(e, "force_serpapi_reindex")
        raise HTTPException(status_code=500, detail=f"Error during SerpAPI reindex: {str(e)}")

@router.get("/admin/test-privacy-search", tags=["Admin"])
async def test_privacy_search():
    """Test privacy policy search functionality"""
    try:
        log_function_call("test_privacy_search")
        
        test_queries = [
            "privacy policy",
            "data protection", 
            "data security",
            "personal information",
            "privacy practices"
        ]
        
        results = {}
        
        for query in test_queries:
            search_results = await vectordb_service.search_privacy_policy(query)
            general_results = await vectordb_service.search_similar(query, top_k=5)
            
            results[query] = {
                "privacy_specific_results": len(search_results),
                "general_results": len(general_results),
                "best_privacy_score": search_results[0].score if search_results else 0,
                "best_general_score": general_results[0].score if general_results else 0,
                "privacy_preview": search_results[0].content[:100] + "..." if search_results else "No content",
                "general_preview": general_results[0].content[:100] + "..." if general_results else "No content"
            }
        
        return {
            "test_results": results,
            "timestamp": datetime.now().isoformat(),
            "extraction_method": "SerpAPI",
            "recommendation": "If privacy results are limited, run /admin/serpapi-reindex to refresh content"
        }
        
    except Exception as e:
        log_error(e, "test_privacy_search")
        raise HTTPException(status_code=500, detail=f"Error during privacy search test: {str(e)}")