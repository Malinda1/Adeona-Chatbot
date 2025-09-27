# Main chatbot logic

# Live SerpAPI chatbot - Real-time web search instead of vectorDB

import asyncio
import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime
import aiohttp
import ssl
import json

from backend.app.config.settings import settings
from backend.app.config.prompts import prompts
from backend.app.services.gemini_service import gemini_service
from backend.app.services.airtable_service import airtable_service
from backend.app.services.googlesheet_service import googlesheet_service
from backend.app.models.chat_models import ChatMessage, ChatResponse, SessionData, ServiceRequest
from backend.app.models.customer import Customer
from backend.app.utils.logger import logger, log_error, log_function_call

class LiveSerpAPIChatbot:
    """Chatbot that uses live SerpAPI searches instead of vectorDB"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.service_booking_steps = ['name', 'email', 'phone', 'address', 'service_details', 'confirmation']
        self.serpapi_key = settings.SERPAPI_API_KEY
        self.serpapi_url = "https://serpapi.com/search"
        
    def get_or_create_session(self, session_id: str) -> SessionData:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData(session_id=session_id)
        return self.sessions[session_id]
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """Main message processing function with live SerpAPI search"""
        try:
            log_function_call("process_message", {
                "message_length": len(message.message),
                "session_id": message.session_id
            })
            
            # Get or create session
            session = self.get_or_create_session(message.session_id or str(uuid.uuid4()))
            session.add_message("user", message.message)
            
            # Check if user is in the middle of service booking
            if session.user_data and session.user_data.step != "completed":
                response_text = await self._handle_service_booking(message.message, session)
            else:
                # Check for cancellation User ID
                message_clean = message.message.strip().upper()
                if (len(message_clean) == 8 and message_clean.isalnum() and 
                    len(session.conversation_history) >= 2):
                    last_assistant_msg = None
                    for msg in reversed(session.conversation_history):
                        if msg.role == "assistant":
                            last_assistant_msg = msg.content
                            break
                    
                    if (last_assistant_msg and 
                        ("User ID" in last_assistant_msg and "cancel" in last_assistant_msg.lower())):
                        logger.info(f"Detected User ID for cancellation: {message_clean}")
                        response_text = await self._process_cancellation_request(message_clean, session)
                    else:
                        # Route based on intent with live search
                        intent_data = await gemini_service.analyze_user_intent(message.message)
                        intent = intent_data.get("intent", "COMPANY_INFO")
                        logger.info(f"Detected intent: {intent}")
                        response_text = await self._route_by_intent(intent, message.message, session)
                else:
                    # Route based on intent with live search
                    intent_data = await gemini_service.analyze_user_intent(message.message)
                    intent = intent_data.get("intent", "COMPANY_INFO")
                    logger.info(f"Detected intent: {intent}")
                    response_text = await self._route_by_intent(intent, message.message, session)
            
            # Generate audio response
            audio_file = await self._generate_audio_response(response_text)
            
            session.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                audio_url=f"/api/v1/audio/{audio_file}" if audio_file else None,
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
    
    async def _route_by_intent(self, intent: str, message: str, session: SessionData) -> str:
        """Route message based on detected intent with live search"""
        if intent == "GREETING":
            return await self._handle_greeting(message)
        elif intent == "SERVICE_BOOKING":
            return await self._handle_service_booking(message, session)
        elif intent == "CANCELLATION":
            return await self._handle_cancellation(message, session)
        elif intent == "CONTACT_REQUEST":
            return await self._handle_contact_request_with_search(message)
        else:  # COMPANY_INFO and OTHER - use live search
            return await self._handle_company_info_with_live_search(message)
    
    async def _handle_greeting(self, message: str) -> str:
        """Handle greeting messages"""
        return "Hello! I'm AdeonaBot, your AI assistant for Adeona Technologies. I can search for the latest information about our services, company details, and help you book services. How can I assist you today?"
    
    async def _search_with_serpapi(self, query: str, site_specific: bool = True) -> List[Dict]:
        """Perform live search using SerpAPI"""
        try:
            log_function_call("_search_with_serpapi", {"query": query[:50], "site_specific": site_specific})
            
            if not self.serpapi_key:
                logger.error("SerpAPI key not configured")
                return []
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Prepare search queries
            search_queries = []
            
            if site_specific:
                # Search within Adeona website first
                search_queries.extend([
                    f'site:adeonatech.net {query}',
                    f'site:adeonatech.net "{query}"',
                    f'"Adeona Technologies" {query}'
                ])
            else:
                # General search for social media, external info
                search_queries.extend([
                    f'"Adeona Technologies" {query}',
                    f'Adeona Technologies {query} site:facebook.com',
                    f'Adeona Technologies {query} site:linkedin.com',
                    f'Adeona Technologies {query} site:twitter.com'
                ])
            
            all_results = []
            
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30)) as session:
                
                for search_query in search_queries:
                    try:
                        params = {
                            'api_key': self.serpapi_key,
                            'engine': 'google',
                            'q': search_query,
                            'num': 5,
                            'hl': 'en',
                            'gl': 'us'
                        }
                        
                        logger.info(f"Searching: {search_query}")
                        
                        async with session.get(self.serpapi_url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if 'organic_results' in data:
                                    for result in data['organic_results']:
                                        result_info = {
                                            'title': result.get('title', ''),
                                            'snippet': result.get('snippet', ''),
                                            'link': result.get('link', ''),
                                            'query': search_query
                                        }
                                        
                                        # Add rich snippet data if available
                                        if 'rich_snippet' in result:
                                            result_info['rich_snippet'] = result['rich_snippet']
                                        
                                        all_results.append(result_info)
                                
                                # Check for featured snippet
                                if 'featured_snippet' in data:
                                    featured = data['featured_snippet']
                                    featured_info = {
                                        'title': 'Featured Result',
                                        'snippet': featured.get('snippet', ''),
                                        'link': featured.get('link', ''),
                                        'query': search_query,
                                        'is_featured': True
                                    }
                                    all_results.insert(0, featured_info)  # Put featured at top
                                
                                logger.info(f"Found {len(data.get('organic_results', []))} results for: {search_query}")
                                
                                # If we found good results from site-specific search, we can break
                                if site_specific and len([r for r in all_results if 'adeonatech.net' in r.get('link', '')]) >= 2:
                                    break
                            
                            else:
                                logger.warning(f"SerpAPI search failed: {response.status}")
                        
                        # Rate limiting - wait between requests
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Search query failed: {search_query} - {e}")
                        continue
            
            logger.info(f"Total search results found: {len(all_results)}")
            return all_results
            
        except Exception as e:
            log_error(e, "_search_with_serpapi")
            return []
    
    async def _handle_company_info_with_live_search(self, message: str) -> str:
        """Handle company information requests with live SerpAPI search"""
        try:
            log_function_call("_handle_company_info_with_live_search", {"query": message[:50]})
            
            message_lower = message.lower().strip()
            
            # Determine if this is a specific query
            is_specific_query = self._is_specific_factual_query(message)
            
            # Check what type of information they're looking for
            is_social_media_query = any(social in message_lower for social in [
                'facebook', 'twitter', 'linkedin', 'instagram', 'social media', 
                'fb', 'social', 'page', 'profile'
            ])
            
            # Perform live search
            logger.info(f"Performing live search for: {message}")
            
            if is_social_media_query:
                # Search for social media presence
                search_results = await self._search_with_serpapi(message, site_specific=False)
            else:
                # Search within company website first
                search_results = await self._search_with_serpapi(message, site_specific=True)
            
            if not search_results:
                logger.warning("No search results found, using fallback")
                return self._get_fallback_response(message, is_specific_query)
            
            # Process search results
            relevant_content = []
            
            for result in search_results[:5]:  # Use top 5 results
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                link = result.get('link', '')
                
                if snippet and len(snippet) > 20:
                    content_item = f"**{title}**\n{snippet}\nSource: {link}"
                    relevant_content.append(content_item)
            
            if not relevant_content:
                return self._get_fallback_response(message, is_specific_query)
            
            # Prepare context for AI response
            search_context = "\n\n---\n\n".join(relevant_content[:3])  # Use top 3 results
            
            # Generate focused response based on query type
            if is_specific_query:
                # For specific questions, be very direct
                prompt = f"""
                Based on this live search information about Adeona Technologies:
                
                {search_context}
                
                User Question: {message}
                
                INSTRUCTIONS:
                - Provide a DIRECT, FOCUSED answer to this specific question
                - Extract the exact information requested
                - Keep response under 100 words
                - Do NOT add extra services or contact details unless asked
                - If the information isn't in the search results, say so clearly
                
                Be precise and direct.
                """
            else:
                # For general queries, be informative but structured
                prompt = f"""
                Based on this live search information about Adeona Technologies:
                
                {search_context}
                
                User Question: {message}
                
                INSTRUCTIONS:
                - Provide a helpful, structured response based on the search results
                - Keep response under 200 words
                - Include relevant links if they provide additional value
                - Focus on answering the user's question directly
                - Only mention contact details if specifically relevant
                """
            
            response = await gemini_service.generate_response(prompt)
            logger.info("Generated response from live search results")
            return response
            
        except Exception as e:
            log_error(e, "_handle_company_info_with_live_search")
            return self._get_fallback_response(message, self._is_specific_factual_query(message))
    
    async def _handle_contact_request_with_search(self, message: str) -> str:
        """Handle contact requests with live search for updated information"""
        try:
            log_function_call("_handle_contact_request_with_search")
            
            # Search for contact information
            contact_results = await self._search_with_serpapi("contact information phone email address", site_specific=True)
            
            if contact_results:
                # Extract contact info from search results
                contact_content = []
                for result in contact_results[:2]:
                    if result.get('snippet'):
                        contact_content.append(result['snippet'])
                
                if contact_content:
                    context = "\n\n".join(contact_content)
                    prompt = f"""
                    Based on this search information:
                    {context}
                    
                    User asked: {message}
                    
                    Extract and provide the contact information for Adeona Technologies in a clear, structured format.
                    Include phone, email, address, and website if available.
                    Keep response focused and under 150 words.
                    """
                    
                    response = await gemini_service.generate_response(prompt)
                    return response
            
            # Fallback contact information
            return """**Contact Adeona Technologies:**
Phone: (+94) 117 433 3333
Email: info@adeonatech.net
Address: 14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100
Website: https://adeonatech.net
Contact Page: https://adeonatech.net/contact"""
                
        except Exception as e:
            log_error(e, "_handle_contact_request_with_search")
            return "Contact Adeona Technologies: Phone (+94) 117 433 3333, Email info@adeonatech.net, Website https://adeonatech.net"
    
    def _is_specific_factual_query(self, message: str) -> bool:
        """Check if the query is asking for a specific fact"""
        specific_indicators = [
            'when', 'what year', 'what date', 'how many', 'where', 'who', 
            'which year', 'what time', 'how long', 'how much', 'what is the',
            'when was', 'when did', 'what was', 'how old', 'founded', 'established',
            'started', 'began', 'beginning', 'inception', 'created'
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in specific_indicators)
    
    def _get_fallback_response(self, message: str, is_specific_query: bool) -> str:
        """Generate fallback responses when search fails"""
        message_lower = message.lower()
        
        # Check for specific topics
        if any(word in message_lower for word in ['service', 'services']):
            if is_specific_query:
                return "Our main services include custom software development, CRM systems, mobile applications, and digital solutions. Visit https://adeonatech.net/service for the complete list."
            else:
                return """**Adeona Technologies Services:**
• Tailored Software Development
• Adeona Foresight CRM
• Mobile & Web Application Development
• Digital Business Solutions
• API Development & Integration

For detailed information: https://adeonatech.net/service"""
        
        elif any(word in message_lower for word in ['founded', 'started', 'began', 'establishment', 'inception', 'year', 'beginning', 'date']):
            return "Adeona Technologies was founded in 2017."
        
        elif any(word in message_lower for word in ['facebook', 'social', 'twitter', 'linkedin']):
            return "I couldn't find current social media links through search. Please visit https://adeonatech.net for official social media links or contact (+94) 117 433 3333 for more information."
        
        elif any(word in message_lower for word in ['contact', 'phone', 'email', 'address']):
            return """**Contact Information:**
Phone: (+94) 117 433 3333
Email: info@adeonatech.net
Address: 14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100
Website: https://adeonatech.net/contact"""
        
        else:
            if is_specific_query:
                return "I couldn't find that specific information through search. Please visit https://adeonatech.net or contact (+94) 117 433 3333 for detailed inquiries."
            else:
                return """Adeona Technologies is a leading IT solutions company in Sri Lanka, specializing in custom software development and digital transformation services.

For specific information: https://adeonatech.net or (+94) 117 433 3333"""
    
    # [Service booking and other methods remain the same as previous version]
    async def _handle_service_booking(self, message: str, session: SessionData) -> str:
        """Handle service booking process"""
        try:
            if not session.user_data:
                session.user_data = ServiceRequest()
                session.user_data.step = "name"
                return "I'd be happy to help you book our services! Please provide your full name."
            
            user_data = session.user_data
            current_step = user_data.step
            
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
                user_data.step = "name"
                return "Let's start the booking process. Please provide your full name."
                
        except Exception as e:
            log_error(e, "_handle_service_booking")
            return "Please provide your name to start booking, or contact us at (+94) 117 433 3333."
    
    async def _collect_name(self, message: str, user_data: ServiceRequest) -> str:
        name = message.strip()
        if len(name) >= 2:
            user_data.name = name
            user_data.step = "email"
            return f"Thank you, {name}! Please provide your email address."
        return "Please provide your full name (at least 2 characters)."
    
    async def _collect_email(self, message: str, user_data: ServiceRequest) -> str:
        email = message.strip()
        if "@" in email and "." in email.split("@")[-1]:
            user_data.email = email
            user_data.step = "phone"
            return "Great! Now please provide your phone number."
        return "Please provide a valid email address."
    
    async def _collect_phone(self, message: str, user_data: ServiceRequest) -> str:
        phone = message.strip()
        clean_phone = ''.join(filter(str.isdigit, phone))
        if len(clean_phone) >= 10:
            user_data.phone = phone
            user_data.step = "address"
            return "Perfect! Please provide your complete address."
        return "Please provide a valid phone number with at least 10 digits."
    
    async def _collect_address(self, message: str, user_data: ServiceRequest) -> str:
        address = message.strip()
        if len(address) >= 5:
            user_data.address = address
            user_data.step = "service_details"
            return "Thank you! Now please describe the specific service you're interested in and any requirements."
        return "Please provide your complete address."
    
    async def _collect_service_details(self, message: str, user_data: ServiceRequest) -> str:
        service_details = message.strip()
        if len(service_details) >= 10:
            user_data.service_details = service_details
            user_data.step = "confirmation"
            
            return f"""Please confirm your details:

Name: {user_data.name}
Email: {user_data.email}
Phone: {user_data.phone}
Address: {user_data.address}
Service Details: {user_data.service_details}

Type 'confirm' to submit your service request, or 'edit' to make changes."""
        return "Please provide detailed service requirements (at least 10 characters)."
    
    async def _handle_confirmation(self, message: str, user_data: ServiceRequest, session: SessionData) -> str:
        message_lower = message.lower().strip()
        
        if message_lower in ['confirm', 'yes', 'confirmed']:
            customer = Customer(
                name=user_data.name,
                email=user_data.email,
                phone=user_data.phone,
                address=user_data.address,
                service_details=user_data.service_details
            )
            
            record_id = await airtable_service.create_customer_record(customer)
            
            if record_id:
                user_data.step = "completed"
                session.user_data = None
                return customer.get_confirmation_message()
            return "There was an error processing your request. Please try again or contact us at (+94) 117 433 3333."
                
        elif message_lower in ['edit', 'no', 'change']:
            user_data.step = "name"
            user_data.name = None
            user_data.email = None
            user_data.phone = None
            user_data.address = None
            user_data.service_details = None
            return "No problem! Let's start over. Please provide your full name."
        return "Please type 'confirm' to submit your request or 'edit' to make changes."
    
    async def _handle_cancellation(self, message: str, session: SessionData) -> str:
        try:
            words = message.split()
            user_id = None
            
            for word in words:
                if len(word) == 8 and word.isalnum():
                    user_id = word.upper()
                    break
            
            if not user_id:
                return "To cancel your service, please provide your 8-character User ID."
            return await self._process_cancellation_request(user_id, session)
                    
        except Exception as e:
            log_error(e, "_handle_cancellation")
            return "Please provide your 8-character User ID to cancel, or contact (+94) 117 433 3333."
    
    async def _process_cancellation_request(self, user_id: str, session: SessionData) -> str:
        try:
            cancellation_result = await airtable_service.process_cancellation(user_id)
            
            if cancellation_result["success"]:
                return cancellation_result["message"]
            else:
                if cancellation_result.get("time_exceeded", False):
                    return f"Your cancellation request cannot be processed as it exceeds the 24-hour window. Please contact us at (+94) 117 433 3333."
                elif cancellation_result["requires_contact"]:
                    return f"{cancellation_result['message']} Contact: (+94) 117 433 3333"
                return cancellation_result["message"]
                    
        except Exception as e:
            log_error(e, "_process_cancellation_request")
            return "Error processing cancellation. Contact (+94) 117 433 3333."
    
    async def _generate_audio_response(self, text: str) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{timestamp}.wav"
            audio_file = await gemini_service.generate_speech(text, output_file=filename)
            return filename if audio_file else None
        except Exception as e:
            log_error(e, "_generate_audio_response")
            return None
    
    async def initialize_services(self):
        """Initialize required services (no vectorDB needed)"""
        try:
            log_function_call("initialize_services")
            
            # Only initialize Google Sheets - no vectorDB needed
            await googlesheet_service.initialize()
            
            logger.info("Services initialized successfully (Live SerpAPI mode - no vectorDB)")
            
        except Exception as e:
            log_error(e, "initialize_services")
            raise e
    
    def get_session_stats(self) -> Dict[str, Any]:
        try:
            active_sessions = len(self.sessions)
            total_messages = sum(len(session.conversation_history) for session in self.sessions.values())
            
            return {
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "mode": "Live SerpAPI Search",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            log_error(e, "get_session_stats")
            return {"active_sessions": 0, "total_messages": 0, "mode": "Live SerpAPI Search", "timestamp": datetime.now().isoformat()}
    
    def cleanup_old_sessions(self, hours: int = 24):
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

# Create global chatbot instance with live search
adeona_chatbot = LiveSerpAPIChatbot()