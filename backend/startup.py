# App startup script

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.chatbot import adeona_chatbot
from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error

async def main():
    """Main startup function"""
    try:
        logger.info("=== Adeona Chatbot Startup ===")
        
        # Validate environment variables
        logger.info("Validating environment variables...")
        settings.validate_settings()
        logger.info("Environment validation completed")
        
        # Initialize all services
        logger.info("Initializing chatbot services...")
        await adeona_chatbot.initialize_services()
        logger.info("Service initialization completed")
        
        # Test basic functionality
        logger.info("Testing basic functionality...")
        test_message = "Hello, tell me about Adeona Technologies"
        
        from app.models.chat_models import ChatMessage
        test_chat = ChatMessage(message=test_message)
        
        response = await adeona_chatbot.process_message(test_chat)
        logger.info(f"Test response generated: {len(response.response)} characters")
        
        logger.info("=== Startup completed successfully ===")
        logger.info("You can now start the FastAPI server with:")
        logger.info("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        
        return True
        
    except Exception as e:
        log_error(e, "startup")
        logger.error("=== Startup failed ===")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)