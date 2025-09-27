# Main chatbot logic

import asyncio
import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime

from backend.app.config.settings import settings
from backend.app.config.prompts import prompts
from backend.app.services.gemini_service import gemini_service
from backendapp.services.vectordb_service import vectordb_service
from backend.app.services.airtable_service import airtable_service
from backend.app.services.googlesheet_service import googlesheet_service
from backend.app.models.chat_models import ChatMessage, ChatResponse, SessionData, ServiceRequest
from backend.app.models.customer import Customer
from backend.app.utils.logger import logger, log_error, log_function_call

class AdeonaChatbot:
    """Main chatbot class for Adeona Technologies"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.service_booking_steps = ['name', 'email', 'phone', 'address', 'service_details', 'confirmation']
        
    def get_or_create_session(self, session_id: str) -> SessionData:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData(session_id=session_id)
        return self.sessions[session_id]
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """Main message processing function"""
        try:
            log_function_call("process_message", {
                "message_length": len(message.message),
                "session_id": message.session_id
            })
            
            # Get or create session
            session = self.get_or_create_session(message.session_id or str(uuid.uuid4()))
            session.add_message("user", message.message)
            
            # Analyze user intent
            intent_data = await gemini_service.analyze_user_intent(message.message)
            intent = intent_data.get("intent", "COMPANY_INFO")
            
            logger.info(f"Detected intent: {intent}")
            
            # Route to appropriate handler
            if intent == "GREETING":
                response_text = await self._handle_greeting(message.message)
            elif intent == "SERVICE_BOOKING":
                response_text = await self._handle_service_booking(message.message, session)
            elif intent == "CANCELLATION":
                response_text = await self._handle_cancellation(message.message, session)
            elif intent == "CONTACT_REQUEST":
                response_text = await self._handle_contact_request(message.message)
            else:  # COMPANY_INFO and OTHER
                response_text = await self._handle_company_info(message.message)
            
            # Generate audio response
            audio_file = await self._generate_audio_response(response_text)
            
            session.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                audio_url=f"/static/audio/{audio_file}" if audio_file else None,
                session_id=session.session_id,
                sources=[]
            )
            
        except Exception as e:
            log_error(e, "process_message")
            error_response = "I apologize for the technical difficulty. Please contact our support team at (+94) 117 433 3333 for immediate assistance."
            return ChatResponse(
                response=error_response,
                session_id=message.session_id or str(uuid.uuid4())
            )
    
    async def _handle_greeting(self, message: str) -> str:
        """Handle greeting messages"""
        try:
            log_function_call("_handle_greeting")
            
            greeting_prompt = f"""
            {prompts.get_system_prompt()}
            
            The user just greeted you with: "{message}"
            
            Respond with a professional welcome message that:
            1. Introduces you as AdeonaBot
            2. Mentions you represent Adeona Technologies
            3. Offers to help with company information or services
            4. Keeps it concise and professional
            """
            
            response = await gemini_service.generate_response(greeting_prompt)
            return response
            
        except Exception as e:
            log_error(e, "_handle_greeting")
            return "Hello! I'm AdeonaBot, your AI assistant for Adeona Technologies. I'm here to help you with information about our IT services and solutions. How can I assist you today?"
    
    async def _handle_company_info(self, message: str) -> str:
        """Handle company information requests"""
        try:
            log_function_call("_handle_company_info")
            
            # Search vector database for relevant content
            search_results = await vectordb_service.search_similar(message, top_k=3)
            
            # Prepare context from search results
            context_parts = []
            for result in search_results:
                context_parts.append(f"Content: {result.content}")
                context_parts.append(f"Source: {result.metadata.get('url', 'Website')}")
                context_parts.append("---")
            
            context = "\n".join(context_parts) if context_parts else "General company information"
            
            # Generate response with context
            full_prompt = f"""
            {prompts.get_system_prompt()}
            {prompts.get_context_prompt(context)}
            
            User Question: {message}
            
            Provide a helpful, accurate response based on the context provided. If you need to direct them to contact information, use:
            - Contact page: https://adeonatech.net/contact  
            - Phone: (+94) 117 433 3333
            - Email: info@adeonatech.net
            """
            
            response = await gemini_service.generate_response(full_prompt)
            return response
            
        except Exception as e:
            log_error(e, "_handle_company_info")
            return "I can help you with information about Adeona Technologies. We offer comprehensive IT solutions including software development, CRM systems, mobile apps, and more. For detailed information, please visit https://adeonatech.net/ or contact us at (+94) 117 433 3333."
    
    async def _handle_contact_request(self, message: str) -> str:
        """Handle contact information requests"""
        try:
            log_function_call("_handle_contact_request")
            
            # Search Google Sheets for contact information
            contact_info = await googlesheet_service.search_contact_info(message)
            
            if contact_info:
                formatted_response = await googlesheet_service.format_contact_response(contact_info)
                
                response_prompt = f"""
                {prompts.get_system_prompt()}
                
                The user asked: "{message}"
                
                Contact information found:
                {formatted_response}
                
                Provide a helpful response that includes the contact information and offers additional assistance.
                """
                
                response = await gemini_service.generate_response(response_prompt)
                return response
            else:
                return f"""Here's how you can contact Adeona Technologies:

Phone: (+94) 117 433 3333
Email: info@adeonatech.net
Address: 14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100

For more contact options and to send us a message, please visit: https://adeonatech.net/contact

Is there anything specific you'd like to know about our services?"""
                
        except Exception as e:
            log_error(e, "_handle_contact_request")
            return "You can contact Adeona Technologies at (+94) 117 433 3333 or email us at info@adeonatech.net. Visit https://adeonatech.net/contact for more information."
    
    async def _handle_service_booking(self, message: str, session: SessionData) -> str:
        """Handle service booking process"""
        try:
            log_function_call("_handle_service_booking")
            
            # Initialize user data if not exists
            if not session.user_data:
                session.user_data = ServiceRequest()
            
            user_data = session.user_data
            current_step = user_data.step
            
            # Process based on current step
            if current_step == "name":
                return await self._collect_name(message, user_data)
            elif current_step == "email":
                return await self._collect_email(message, user_data)
            elif current_step == "phone":
                return await self._collect_phone(message, user_data)
            elif current_step == "address":
                return await self._collect_address(message, user_data)
            elif current_step == "service_details":
                return await self._collect_service_details(message, user_data)
            elif current_step == "confirmation":
                return await self._handle_confirmation(message, user_data, session)
            else:
                # Initial service booking request
                user_data.step = "name"
                return "I'd be happy to help you with our services! To get started, please provide your full name."
                
        except Exception as e:
            log_error(e, "_handle_service_booking")
            return "I'd like to help you with our services. Please provide your name to get started, or contact us directly at (+94) 117 433 3333."
    
    async def _collect_name(self, message: str, user_data: ServiceRequest) -> str:
        """Collect customer name"""
        name = message.strip()
        if len(name) >= 2:
            user_data.name = name
            user_data.step = "email"
            return f"Thank you, {name}! Please provide your email address."
        else:
            return "Please provide your full name (at least 2 characters)."
    
    async def _collect_email(self, message: str, user_data: ServiceRequest) -> str:
        """Collect customer email"""
        email = message.strip()
        if "@" in email and "." in email.split("@")[-1]:
            user_data.email = email
            user_data.step = "phone"
            return "Great! Now please provide your phone number."
        else:
            return "Please provide a valid email address."
    
    async def _collect_phone(self, message: str, user_data: ServiceRequest) -> str:
        """Collect customer phone"""
        phone = message.strip()
        clean_phone = ''.join(filter(str.isdigit, phone))
        if len(clean_phone) >= 10:
            user_data.phone = phone
            user_data.step = "address"
            return "Perfect! Please provide your complete address."
        else:
            return "Please provide a valid phone number with at least 10 digits."
    
    async def _collect_address(self, message: str, user_data: ServiceRequest) -> str:
        """Collect customer address"""
        address = message.strip()
        if len(address) >= 5:
            user_data.address = address
            user_data.step = "service_details"
            return "Thank you! Now please describe the specific service you're interested in and any requirements you have."
        else:
            return "Please provide your complete address."
    
    async def _collect_service_details(self, message: str, user_data: ServiceRequest) -> str:
        """Collect service details"""
        service_details = message.strip()
        if len(service_details) >= 10:
            user_data.service_details = service_details
            user_data.step = "confirmation"
            
            # Show confirmation details
            return f"""Perfect! Please confirm your details:

Name: {user_data.name}
Email: {user_data.email}
Phone: {user_data.phone}
Address: {user_data.address}
Service Details: {user_data.service_details}

Type 'confirm' to submit your service request, or 'edit' if you need to make changes."""
        else:
            return "Please provide detailed service requirements (at least 10 characters)."
    
    async def _handle_confirmation(self, message: str, user_data: ServiceRequest, session: SessionData) -> str:
        """Handle booking confirmation"""
        message_lower = message.lower().strip()
        
        if message_lower in ['confirm', 'yes', 'confirmed']:
            # Create customer record
            customer = Customer(
                name=user_data.name,
                email=user_data.email,
                phone=user_data.phone,
                address=user_data.address,
                service_details=user_data.service_details
            )
            
            # Save to Airtable
            record_id = await airtable_service.create_customer_record(customer)
            
            if record_id:
                # Clear session data
                session.user_data = None
                return customer.get_confirmation_message()
            else:
                return "There was an error processing your request. Please try again or contact us at (+94) 117 433 3333."
                
        elif message_lower in ['edit', 'no', 'change']:
            # Reset to name collection
            user_data.step = "name"
            user_data.name = None
            user_data.email = None
            user_data.phone = None
            user_data.address = None
            user_data.service_details = None
            return "No problem! Let's start over. Please provide your full name."
        else:
            return "Please type 'confirm' to submit your request or 'edit' to make changes."
    
    async def _handle_cancellation(self, message: str, session: SessionData) -> str:
        """Handle service cancellation requests"""
        try:
            log_function_call("_handle_cancellation")
            
            # Check if user provided User ID in the message
            words = message.split()
            user_id = None
            
            # Look for User ID in message
            for word in words:
                if len(word) == 8 and word.isalnum():  # User IDs are 8 character alphanumeric
                    user_id = word.upper()
                    break
            
            if not user_id:
                return "To cancel your service, I need your User ID. Please provide the 8-character User ID you received when booking the service."
            
            # Process cancellation
            cancellation_result = await airtable_service.process_cancellation(user_id)
            
            if cancellation_result["success"]:
                return cancellation_result["message"]
            else:
                if cancellation_result["requires_contact"]:
                    return f"{cancellation_result['message']} Please contact us at (+94) 117 433 3333 for assistance."
                else:
                    return cancellation_result["message"]
                    
        except Exception as e:
            log_error(e, "_handle_cancellation")
            return "I can help you cancel your service. Please provide your 8-character User ID, or contact us at (+94) 117 433 3333."
    
    async def _generate_audio_response(self, text: str) -> Optional[str]:
        """Generate audio response from text"""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{timestamp}.wav"
            
            # Generate speech
            audio_file = await gemini_service.generate_speech(text, output_file=filename)
            
            if audio_file:
                return filename
            return None
            
        except Exception as e:
            log_error(e, "_generate_audio_response")
            return None
    
    async def initialize_services(self):
        """Initialize all required services"""
        try:
            log_function_call("initialize_services")
            
            # Initialize Vector DB
            await vectordb_service.initialize()
            
            # Index website content if needed
            await vectordb_service.index_website_content()
            
            # Initialize Google Sheets
            await googlesheet_service.initialize()
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            log_error(e, "initialize_services")
            raise e
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get chatbot session statistics"""
        try:
            active_sessions = len(self.sessions)
            total_messages = sum(len(session.conversation_history) for session in self.sessions.values())
            
            return {
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            log_error(e, "get_session_stats")
            return {"active_sessions": 0, "total_messages": 0, "timestamp": datetime.now().isoformat()}
    
    def cleanup_old_sessions(self, hours: int = 24):
        """Clean up old inactive sessions"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            old_sessions = []
            for session_id, session in self.sessions.items():
                if session.last_activity < cutoff_time:
                    old_sessions.append(session_id)
            
            for session_id in old_sessions:
                del self.sessions[session_id]
            
            logger.info(f"Cleaned up {len(old_sessions)} old sessions")
            
        except Exception as e:
            log_error(e, "cleanup_old_sessions")

# Create global chatbot instance
adeona_chatbot = AdeonaChatbot()