# Main chatbot logic



import asyncio
import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime
import re
import os

from backend.app.config.settings import settings
from backend.app.config.prompts import prompts
from backend.app.services.gemini_service import gemini_service
from backend.app.services.vectordb_service import vectordb_service
from backend.app.services.serpapi_service import serpapi_service
from backend.app.services.airtable_service import airtable_service
from backend.app.services.googlesheet_service import googlesheet_service
from backend.app.models.chat_models import ChatMessage, ChatResponse, SessionData, ServiceRequest
from backend.app.models.customer import Customer
from backend.app.utils.logger import logger, log_error, log_function_call

class EnhancedAdeonaChatbot:
    
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.service_booking_steps = ['name', 'email', 'phone', 'address', 'service_details', 'confirmation']
        
        # COMPLETE service list for Adeona Technologies
        self.complete_services = [
            "Tailored Software Development",
            "Adeona Foresight CRM", 
            "Digital Bill",
            "Digital Business Card",
            "Value Added Service Development (VAS)",
            "Cross-Platform Mobile and Web Application Development",
            "In-App and In-Web Advertising Solutions",
            "API Design and Implementation",
            "Inventory Management Solutions", 
            "Bulk SMS and Rich Messaging",
            "Fleet Management Solutions",
            "Website Builder Tool",
            "Restaurant Management System",
            "3CX Business Communication",
            "Scratch Card Solution",
            "Lead Manager",
            "eSMS",
            "In-App Advertising Platform", 
            "eRL 2.0 Integration",
            "Spare Part Verification System",
            "Bulk OTA Setting Update Platform"
        ]
        
        # knowledge base with social media links
        self.basic_knowledge = {
            "identity": "I'm AdeonaBot, the official AI assistant for Adeona Technologies.",
            "company": "Adeona Technologies",
            "founded": "2017",
            "location": "Colombo, Sri Lanka",
            "phone": "(+94) 117 433 3333",
            "email": "info@adeonatech.net",
            "website": "https://adeonatech.net/",
            "privacy_policy": "https://adeonatech.net/privacy-policy",
            "address": "14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100",
            "services_count": len(self.complete_services),
            # Social media links
            "linkedin": "https://www.linkedin.com/company/adeona-technologies/",
            "twitter": "https://twitter.com/adeona_tech",
            "facebook": "https://web.facebook.com/adeonatech"
        }
    
    def get_or_create_session(self, session_id: str) -> SessionData:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData(session_id=session_id)
        return self.sessions[session_id]
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
       
        try:
            log_function_call("process_message", {
                "message_length": len(message.message),
                "session_id": message.session_id
            })
            
            # Get or create session
            session = self.get_or_create_session(message.session_id or str(uuid.uuid4()))
            session.add_message("user", message.message)
            
            # FIXED: Check if user is in cancellation process FIRST
            if hasattr(session, 'cancellation_pending') and session.cancellation_pending:
                response_text = await self._handle_cancellation_userid_input(message.message, session)
            # Check if user is in service booking process
            elif session.user_data and session.user_data.step != "completed":
                response_text = await self._handle_service_booking(message.message, session)
            else:
                # Process normal message with enhanced routing
                response_text = await self._route_message_enhanced(message.message, session)
            
            # Generate audio response with error handling
            audio_filename = await self._generate_audio_response(response_text)
            audio_url = None
            
            if audio_filename:
                audio_url = f"/api/v1/audio/{audio_filename}"
                logger.info(f"Audio URL generated: {audio_url}")
            else:
                logger.warning("Audio generation failed - proceeding without audio")
            
            session.add_message("assistant", response_text)
            
            return ChatResponse(
                response=response_text,
                audio_url=audio_url,
                session_id=session.session_id,
                sources=[]
            )
            
        except Exception as e:
            log_error(e, "process_message")
            error_response = f"I apologize for the technical difficulty. Please contact our support team at {self.basic_knowledge['phone']} for immediate assistance."
            return ChatResponse(
                response=error_response,
                session_id=message.session_id or str(uuid.uuid4())
            )
    
    async def _route_message_enhanced(self, message: str, session: SessionData) -> str:
       
        try:
            message_lower = message.lower().strip()
            
            # 1. Handle context-aware queries (this company = Adeona Technologies)
            processed_message = self._process_context_aware_query(message)
            
            # 2. Handle basic info questions immediately (no search needed)
            if self._is_basic_info_question(message_lower):
                return self._handle_basic_info(message_lower)
            
            # 3. Handle simple greetings
            if self._is_simple_greeting(message_lower):
                return self._handle_greeting()
            
            # Handle cancellation requests FIRST (highest priority)
            if self._is_cancellation_request(message_lower):
                return await self._handle_cancellation_request(processed_message, session)
            
            # 5. Handle social media requests
            if self._is_social_media_request(message_lower):
                return await self._handle_social_media_request(processed_message)
            
            # 6. Handle contact requests
            if self._is_contact_request(message_lower):
                return self._handle_contact_request(processed_message)
            
            # 7. Check for service booking intent (after cancellation check)
            if self._is_service_booking_request(message_lower):
                return await self._initiate_service_booking(session)
            
            # 8. Handle service-related questions with comprehensive search
            if self._is_service_inquiry(message_lower):
                return await self._handle_service_inquiry(processed_message)
            
            # 9. Handle company questions with intelligent search and fallback
            return await self._handle_company_question_enhanced(processed_message)
            
        except Exception as e:
            log_error(e, "_route_message_enhanced")
            return f"I apologize, but I'm having trouble processing your request. Please contact us at {self.basic_knowledge['phone']} for assistance."
    
    def _process_context_aware_query(self, message: str) -> str:
        
        processed_message = message
        
        # Replace context references with explicit company name
        replacements = {
            'this company': 'Adeona Technologies',
            'the company': 'Adeona Technologies', 
            'your company': 'Adeona Technologies',
            'you guys': 'Adeona Technologies',
            'your services': 'Adeona Technologies services',
            'your solutions': 'Adeona Technologies solutions'
        }
        
        for old_phrase, new_phrase in replacements.items():
            processed_message = processed_message.replace(old_phrase, new_phrase)
        
        if processed_message != message:
            logger.info(f"Context-aware processing: '{message[:50]}...' -> '{processed_message[:50]}...'")
        
        return processed_message
    
    def _is_cancellation_request(self, message: str) -> bool:
        """cancellation detection with higher accuracy"""
        cancellation_patterns = [
            # Direct cancellation phrases
            r'\b(cancel|stop|remove|delete)\b.*\b(service|order|booking|subscription|request)\b',
            r'\b(cancel my|stop my|remove my|delete my)\b',
            r'\b(how to cancel|want to cancel|need to cancel|i want to cancel|i need to cancel)\b',
            r'\b(cancel the|stop the|remove the)\b.*\b(service|order|booking)\b',
            r'\bcancel\b.*\b(my service|my order|my booking|the service|the order)\b',
            
            # User ID with cancel context
            r'\b[A-Z0-9]{8}\b.*\bcancel\b',
            r'\bcancel\b.*\b[A-Z0-9]{8}\b',
            
            # Specific cancellation requests
            r'\bi want to cancel\b',
            r'\bi need to cancel\b',
            r'\bplease cancel\b',
            r'\bcancel it\b',
            r'\bcancel that\b'
        ]
        
        # Check each pattern
        for pattern in cancellation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                logger.info(f"Cancellation detected via pattern: {pattern}")
                return True
        
        # Also check for simple "cancel" with context
        if 'cancel' in message and len(message.split()) <= 5:
            logger.info("Simple cancellation request detected")
            return True
        
        return False
    
    def _is_social_media_request(self, message: str) -> bool:
        """Check if the message is asking for social media profiles"""
        social_indicators = [
            'facebook', 'fb', 'facebook profile', 'facebook page', 'facebook account',
            'twitter', 'x profile', 'twitter profile', 'twitter account', 'x account',
            'linkedin', 'linkedin profile', 'linkedin page', 'linkedin account',
            'instagram', 'insta', 'instagram profile', 'instagram account',
            'social media', 'social profiles', 'social accounts'
        ]
        return any(indicator in message for indicator in social_indicators)
    
    def _is_contact_request(self, message: str) -> bool:
        """Check if the message is asking for contact information"""
        contact_indicators = [
            'phone number', 'contact number', 'telephone', 'call',
            'email address', 'email', 'contact email',
            'contact info', 'contact details', 'how to contact',
            'reach you', 'get in touch', 'address', 'location'
        ]
        return any(indicator in message for indicator in contact_indicators)
    
    async def _handle_social_media_request(self, message: str) -> str:
        """Handle social media profile requests with VectorDB search fallback"""
        try:
            log_function_call("_handle_social_media_request", {"query": message[:50]})
            
            message_lower = message.lower()
            
            # Check for specific social media platform requests
            if any(term in message_lower for term in ['facebook', 'fb']):
                # First try to search VectorDB for Facebook info
                try:
                    search_results, used_fallback = await vectordb_service.search_with_fallback(
                        "facebook profile social media", top_k=5
                    )
                    
                    if search_results and any('facebook' in result.content.lower() for result in search_results):
                        # Extract Facebook link from search results if found
                        for result in search_results:
                            if 'facebook' in result.content.lower() and 'facebook.com' in result.content:
                                return f"Here's Adeona Technologies Facebook profile: {self.basic_knowledge['facebook']}\n\nYou can also find us on:\n• LinkedIn: {self.basic_knowledge['linkedin']}\n• Twitter/X: {self.basic_knowledge['twitter']}"
                except Exception:
                    pass  # Fall back to basic response
                
                return f"Here's Adeona Technologies Facebook profile:\n🔗 **Facebook:** {self.basic_knowledge['facebook']}\n\nYou can also connect with us on:\n• LinkedIn: {self.basic_knowledge['linkedin']}\n• Twitter/X: {self.basic_knowledge['twitter']}"
            
            elif any(term in message_lower for term in ['twitter', 'x profile', 'x account']):
                return f"Here's Adeona Technologies Twitter/X profile:\n🔗 **Twitter/X:** {self.basic_knowledge['twitter']}\n\nYou can also find us on:\n• Facebook: {self.basic_knowledge['facebook']}\n• LinkedIn: {self.basic_knowledge['linkedin']}"
            
            elif any(term in message_lower for term in ['linkedin']):
                return f"Here's Adeona Technologies LinkedIn profile:\n🔗 **LinkedIn:** {self.basic_knowledge['linkedin']}\n\nYou can also connect with us on:\n• Facebook: {self.basic_knowledge['facebook']}\n• Twitter/X: {self.basic_knowledge['twitter']}"
            
            else:
                # General social media request - provide all
                return f"""Here are Adeona Technologies social media profiles:

🔗 **Facebook:** {self.basic_knowledge['facebook']}
🔗 **LinkedIn:** {self.basic_knowledge['linkedin']} 
🔗 **Twitter/X:** {self.basic_knowledge['twitter']}

Connect with us to stay updated on our latest services, projects, and technology insights!

**Other Contact Methods:**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}
🌐 Website: {self.basic_knowledge['website']}"""
            
        except Exception as e:
            log_error(e, "_handle_social_media_request")
            return f"""Here are Adeona Technologies social media profiles:

🔗 **Facebook:** {self.basic_knowledge['facebook']}
🔗 **LinkedIn:** {self.basic_knowledge['linkedin']}
🔗 **Twitter/X:** {self.basic_knowledge['twitter']}

For more information, visit our website: {self.basic_knowledge['website']}"""
    
    def _handle_contact_request(self, message: str) -> str:
        """Handle contact information requests"""
        message_lower = message.lower()
        
        if any(term in message_lower for term in ['phone', 'number', 'call', 'telephone']):
            return f"You can call Adeona Technologies at: **{self.basic_knowledge['phone']}**\n\nOther contact methods:\n📧 Email: {self.basic_knowledge['email']}\n🌐 Website: {self.basic_knowledge['website']}"
        
        elif any(term in message_lower for term in ['email', 'mail']):
            return f"You can email Adeona Technologies at: **{self.basic_knowledge['email']}**\n\nOther contact methods:\n📞 Phone: {self.basic_knowledge['phone']}\n🌐 Website: {self.basic_knowledge['website']}"
        
        elif any(term in message_lower for term in ['address', 'location', 'office']):
            return f"Adeona Technologies office location:\n📍 **Address:** {self.basic_knowledge['address']}\n\nContact us:\n📞 Phone: {self.basic_knowledge['phone']}\n📧 Email: {self.basic_knowledge['email']}"
        
        else:
            return f"""**Contact Adeona Technologies:**

📞 **Phone:** {self.basic_knowledge['phone']}
📧 **Email:** {self.basic_knowledge['email']}
🌐 **Website:** {self.basic_knowledge['website']}
📍 **Address:** {self.basic_knowledge['address']}

**Social Media:**
• Facebook: {self.basic_knowledge['facebook']}
• LinkedIn: {self.basic_knowledge['linkedin']}
• Twitter/X: {self.basic_knowledge['twitter']}

How can we assist you today?"""
    
    def _is_service_inquiry(self, message: str) -> bool:
        """Check if the message is asking about services"""
        service_indicators = [
            'what services', 'what do you offer', 'what can you do',
            'services do you provide', 'what are your services',
            'list of services', 'available services', 'services offered',
            'what solutions', 'what kind of services', 'service list'
        ]
        return any(indicator in message for indicator in service_indicators)
    
    async def _handle_service_inquiry(self, message: str) -> str:
        """Handle service inquiries with comprehensive search and fallback"""
        try:
            log_function_call("_handle_service_inquiry", {"query": message[:50]})
            
            # First, try to get information from VectorDB
            try:
                search_results, used_fallback = await vectordb_service.search_with_fallback(
                    f"services solutions offerings {message}", 
                    top_k=15
                )
                
                if search_results:
                    # Extract service information from search results
                    context = self._prepare_service_context(search_results)
                    
                    # Generate comprehensive response about services
                    service_prompt = f"""Based on this verified information about Adeona Technologies services, provide a comprehensive answer about our services.

ADEONA SERVICES CONTEXT:
{context}

COMPLETE SERVICE LIST (ensure all are mentioned if relevant):
{', '.join(self.complete_services)}

USER QUESTION: {message}

Provide a comprehensive response that:
1. Lists the relevant services clearly
2. Gives brief descriptions based on the context
3. Mentions we have {len(self.complete_services)} total services
4. Includes contact information for detailed inquiries

Response format:
- Start with a brief overview
- List services in categories if possible
- End with contact information"""

                    response = await gemini_service.generate_response(service_prompt)
                    
                    if used_fallback:
                        response += f"\n\nFor the most up-to-date service information, visit: {self.basic_knowledge['website']}"
                    
                    return response
            except Exception:
                pass  # Fall back to complete service list
            
            # If no search results or error, provide comprehensive service list from basic knowledge
            return self._provide_complete_service_list()
            
        except Exception as e:
            log_error(e, "_handle_service_inquiry")
            return self._provide_complete_service_list()
    
    def _prepare_service_context(self, search_results) -> str:
        """Prepare context specifically focused on services"""
        service_context_parts = []
        
        for result in search_results:
            content = result.content.strip()
            
            # Prioritize content that mentions services
            if any(word in content.lower() for word in ['service', 'solution', 'development', 'system']):
                if len(content) > 300:
                    content = content[:300] + "..."
                service_context_parts.append(content)
        
        return "\n\n".join(service_context_parts[:8])  # Use top 8 service-related results
    
    def _provide_complete_service_list(self) -> str:
        """Provide complete service list when search fails"""
        return f"""Adeona Technologies offers {len(self.complete_services)} comprehensive IT solutions and services:

**Core Services:**

**Software Development:**
• Tailored Software Development
• Cross-Platform Mobile and Web Application Development
• API Design and Implementation

**CRM & Business Solutions:**
• Adeona Foresight CRM
• Lead Manager
• Inventory Management Solutions
• Restaurant Management System

**Digital Solutions:**
• Digital Bill
• Digital Business Card
• Website Builder Tool

**Communication & Marketing:**
• Bulk SMS and Rich Messaging
• 3CX Business Communication
• In-App and In-Web Advertising Solutions
• In-App Advertising Platform

**Specialized Systems:**
• Fleet Management Solutions
• Value Added Service Development (VAS)
• Scratch Card Solution
• eSMS
• eRL 2.0 Integration
• Spare Part Verification System
• Bulk OTA Setting Update Platform

**Get Detailed Information:**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}
🌐 Website: {self.basic_knowledge['website']}

Would you like more information about any specific service or would you like to book a consultation?"""
    
    async def _handle_company_question_enhanced(self, message: str) -> str:
        """Handle company questions with intelligent search and better fallback"""
        try:
            log_function_call("handle_company_question_enhanced", {"query": message[:50]})
            
            # Use enhanced search with fallback
            try:
                search_results, used_fallback = await vectordb_service.search_with_fallback(message, top_k=12)
                
                if not search_results:
                    logger.warning("No search results found, using basic fallback")
                    return self._provide_enhanced_fallback_response(message)
                
                # Filter and prioritize results
                high_quality_results = [r for r in search_results if r.score > 0.8]
                moderate_results = [r for r in search_results if r.score > 0.7]
                
                # Use the best available results
                best_results = high_quality_results if high_quality_results else moderate_results[:5]
                
                if not best_results:
                    logger.info("Low quality results, using enhanced fallback")
                    return self._provide_enhanced_fallback_response(message)
                
                # Generate contextual response
                context = self._prepare_enhanced_context(best_results)
                
                enhanced_prompt = f"""You are AdeonaBot for Adeona Technologies. Based on this verified information from adeonatech.net, provide a comprehensive and accurate answer.

VERIFIED ADEONA TECHNOLOGIES INFORMATION:
{context}

USER QUESTION: {message}

INSTRUCTIONS:
- Provide a direct, comprehensive answer using the verified information
- Include specific details from the context when relevant
- Maintain professional but friendly tone
- If information is limited, acknowledge this and provide contact details
- Always ensure the response is helpful and complete

ADEONA CONTACT INFO (include when helpful):
• Phone: {self.basic_knowledge['phone']}
• Email: {self.basic_knowledge['email']}
• Website: {self.basic_knowledge['website']}
• Privacy Policy: {self.basic_knowledge['privacy_policy']}

Provide a comprehensive, accurate response:"""

                response = await gemini_service.generate_response(enhanced_prompt)
                
                # Add source note if SerpAPI was used
                if used_fallback:
                    response += f"\n\n*This information includes real-time updates. For the latest details, visit: {self.basic_knowledge['website']}*"
                
                logger.info(f"Generated enhanced company response using {'local+SerpAPI' if used_fallback else 'local'} data")
                return response
            except Exception:
                return self._provide_enhanced_fallback_response(message)
            
        except Exception as e:
            log_error(e, "_handle_company_question_enhanced")
            return self._provide_enhanced_fallback_response(message)
    
    def _prepare_enhanced_context(self, search_results) -> str:
        """Prepare enhanced context from search results"""
        context_parts = []
        
        for i, result in enumerate(search_results):
            content = result.content.strip()
            source = result.metadata.get('data_source', 'unknown')
            page_type = result.metadata.get('page_type', 'general')
            
            # Clean and format content
            if len(content) > 400:
                content = content[:400] + "..."
            
            # Add context with source info
            context_parts.append(f"[{page_type.upper()}] {content}")
        
        return "\n\n".join(context_parts)
    
    def _provide_enhanced_fallback_response(self, message: str) -> str:
        """Provide better fallback response when search fails"""
        message_lower = message.lower()
        
        # Categorize the question and provide relevant information
        if any(term in message_lower for term in ['service', 'solution', 'software', 'development', 'what do', 'what can']):
            return self._provide_complete_service_list()
        
        elif any(term in message_lower for term in ['privacy', 'policy', 'data', 'protection']):
            return f"""For comprehensive privacy policy information, please visit our dedicated privacy policy page: {self.basic_knowledge['privacy_policy']}

Adeona Technologies is committed to:
• Protecting your personal information
• Maintaining data security standards
• Transparent privacy practices
• Compliance with data protection regulations

For specific privacy questions:
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}

Our privacy policy covers all aspects of how we collect, use, and protect your data."""
        
        elif any(term in message_lower for term in ['about', 'company', 'history', 'founded', 'who are']):
            return f"""**About Adeona Technologies**

Adeona Technologies is a leading IT solutions company established in {self.basic_knowledge['founded']} and based in {self.basic_knowledge['location']}.

**Company Overview:**
• Founded: {self.basic_knowledge['founded']}
• Location: {self.basic_knowledge['address']}
• Industry: IT Solutions & Software Development
• Services: {len(self.complete_services)} comprehensive solutions

**Our Focus:**
We specialize in custom software development, CRM systems, mobile applications, and digital transformation solutions for businesses across various industries.

**Get in Touch:**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}
🌐 Website: {self.basic_knowledge['website']}

For detailed company information and case studies, visit our website or contact us directly."""
        
        elif any(term in message_lower for term in ['contact', 'phone', 'email', 'address', 'reach']):
            return f"""**Contact Adeona Technologies**

📞 **Phone:** {self.basic_knowledge['phone']}
📧 **Email:** {self.basic_knowledge['email']}
🌐 **Website:** {self.basic_knowledge['website']}
📍 **Address:** {self.basic_knowledge['address']}

**Business Hours:** Contact us anytime - we're here to help!

**Online Resources:**
• Website: {self.basic_knowledge['website']}
• Privacy Policy: {self.basic_knowledge['privacy_policy']}

How can we assist you today?"""
        
        else:
            return f"""I'd be happy to help you with information about Adeona Technologies! 

For detailed information about your specific inquiry, please:

**Contact Us Directly:**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}
🌐 Website: {self.basic_knowledge['website']}

**Quick Information:**
• **Founded:** {self.basic_knowledge['founded']} in {self.basic_knowledge['location']}
• **Services:** {len(self.complete_services)} comprehensive IT solutions
• **Specialties:** Custom software, CRM systems, mobile apps

**Popular Topics:**
• Services and solutions offered
• Company background and expertise  
• Privacy policy and data protection
• Service booking and consultations

What specific aspect of Adeona Technologies would you like to know more about?"""
    
    # Keep existing methods for basic info, greetings, booking, etc.
    def _is_basic_info_question(self, message: str) -> bool:
        """Check for basic information questions"""
        basic_indicators = [
            "who are you", "what is your name", "your name", "bot name",
            "phone number", "contact number", "email address", "contact email",
            "address", "location", "where are you", "office address",
            "when founded", "founded", "established when",
            # Don't include social media here - handle separately
        ]
        return any(indicator in message for indicator in basic_indicators)
    
    def _handle_basic_info(self, message: str) -> str:
        """Handle basic information questions immediately"""
        if any(term in message for term in ["who are you", "your name", "bot name"]):
            return f"{self.basic_knowledge['identity']} I'm here to help you with information about our IT solutions and services."
        
        elif any(term in message for term in ["phone", "contact number", "call"]):
            return f"You can reach Adeona Technologies at: {self.basic_knowledge['phone']}"
        
        elif any(term in message for term in ["email", "mail"]):
            return f"Our email address is: {self.basic_knowledge['email']}"
        
        elif any(term in message for term in ["address", "location", "office", "where"]):
            return f"Adeona Technologies is located at: {self.basic_knowledge['address']}"
        
        elif any(term in message for term in ["founded", "established", "when"]):
            return f"Adeona Technologies was founded in {self.basic_knowledge['founded']} in {self.basic_knowledge['location']}."
        
        else:
            return f"""Here's the basic information about Adeona Technologies:

**Company:** {self.basic_knowledge['company']}
**Founded:** {self.basic_knowledge['founded']}
**Location:** {self.basic_knowledge['location']}
**Phone:** {self.basic_knowledge['phone']}
**Email:** {self.basic_knowledge['email']}
**Website:** {self.basic_knowledge['website']}

How can I help you with more specific information?"""
    
    def _is_simple_greeting(self, message: str) -> bool:
        """Check for simple greetings only"""
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        return any(greeting in message for greeting in greetings) and len(message.split()) <= 3
    
    def _handle_greeting(self) -> str:
        """Handle greeting messages"""
        return f"""Hello! Welcome to Adeona Technologies. {self.basic_knowledge['identity']}

Adeona Technologies is a leading IT solutions company in Sri Lanka, specializing in custom software development and digital transformation since {self.basic_knowledge['founded']}.

I can help you with:
• Information about our {len(self.complete_services)} services and solutions
• Company background and expertise  
• Service booking and inquiries
• Technical capabilities and projects

What would you like to know about Adeona Technologies?"""
    
    def _is_service_booking_request(self, message: str) -> bool:
        """Check for service booking intent (exclude social media and cancellation requests)"""
        message_lower = message.lower()
        
        # First check if it's a cancellation request - if yes, don't treat as booking
        if self._is_cancellation_request(message_lower):
            return False
        
        # Check if it's a social media request - if yes, don't treat as booking
        if self._is_social_media_request(message_lower):
            return False
        
        booking_indicators = [
            "book", "order", "purchase", "buy", "get service", "need service",
            "want service", "hire", "request service", "i want to", "i need to"
        ]
        return any(indicator in message_lower for indicator in booking_indicators)
    
    async def _handle_cancellation_request(self, message: str, session: SessionData) -> str:
        """Handle cancellation requests with User ID verification and session tracking"""
        try:
            log_function_call("_handle_cancellation_request", {"message": message[:50]})
            
            message_lower = message.lower().strip()
            
            # Check if User ID is provided in the message
            user_id = self._extract_user_id(message)
            
            if user_id:
                # User ID found, process cancellation directly
                logger.info(f"Processing cancellation for User ID: {user_id}")
                # Clear any pending cancellation state
                session.cancellation_pending = False
                return await self._process_cancellation_with_userid(user_id)
            else:
                # No User ID found, ask for it and set session state
                logger.info("Setting cancellation pending state - waiting for User ID")
                session.cancellation_pending = True  # FIXED: Set session state
                return """To cancel your service, I need your **User ID**.

Please provide your **8-character User ID** (e.g., ABC12345). You can find this in:
• Your booking confirmation email
• SMS confirmation message  
• Service booking receipt

Once you provide your User ID, I'll check if your service can be cancelled (services can be cancelled within 24 hours of booking)."""
                    
        except Exception as e:
            log_error(e, "_handle_cancellation_request")
            session.cancellation_pending = False  # Clear state on error
            return f"I apologize for the error. Please contact our support team at **{self.basic_knowledge['phone']}** for cancellation assistance."
    
    async def _handle_cancellation_userid_input(self, message: str, session: SessionData) -> str:
        """Handle User ID input when user is in cancellation flow"""
        try:
            log_function_call("_handle_cancellation_userid_input", {"message": message[:20]})
            
            # Extract User ID from the message
            user_id = self._extract_user_id(message)
            
            if not user_id:
                # Check if the entire message might be a User ID
                clean_message = message.strip().upper()
                if len(clean_message) == 8 and clean_message.isalnum():
                    user_id = clean_message
            
            if user_id:
                # Found User ID, process cancellation
                logger.info(f"Processing cancellation for User ID from session: {user_id}")
                session.cancellation_pending = False  # Clear the state
                return await self._process_cancellation_with_userid(user_id)
            else:
                # Invalid User ID format
                return """ **Invalid User ID Format**

Please provide a valid **8-character User ID** (letters and numbers only).

Example: ABC12345 or XYZ98765

You can find your User ID in:
• Your booking confirmation email
• SMS confirmation message
• Service booking receipt

Or contact our support team at **{self.basic_knowledge['phone']}** for assistance."""
                
        except Exception as e:
            log_error(e, "_handle_cancellation_userid_input")
            session.cancellation_pending = False  # Clear state on error
            return f"I apologize for the error. Please contact our support team at **{self.basic_knowledge['phone']}** for cancellation assistance."
    
    def _extract_user_id(self, message: str) -> Optional[str]:
        """ENHANCED: Extract User ID from message with better pattern matching"""
        try:
            import re
            
            # Clean the message
            clean_message = message.strip().upper()
            
            # First check if the entire message is just a User ID (8 characters, alphanumeric)
            if len(clean_message) == 8 and clean_message.isalnum():
                logger.info(f"User ID extracted from entire message: {clean_message}")
                return clean_message
            
            # Look for 8-character alphanumeric User ID pattern in text
            user_id_pattern = r'\b[A-Z0-9]{8}\b'
            matches = re.findall(user_id_pattern, clean_message)
            
            if matches:
                user_id = matches[0]
                logger.info(f"User ID extracted from message pattern: {user_id}")
                return user_id
            
            # Also try to find patterns like "ABC12345" even if surrounded by text
            extended_pattern = r'[A-Z]{2,4}[0-9]{4,6}'
            extended_matches = re.findall(extended_pattern, clean_message)
            
            for match in extended_matches:
                if len(match) == 8:
                    logger.info(f"User ID extracted from extended pattern: {match}")
                    return match
            
            return None
            
        except Exception as e:
            log_error(e, "_extract_user_id")
            return None
    
    async def _process_cancellation_with_userid(self, user_id: str) -> str:
        """Process cancellation with provided User ID"""
        try:
            log_function_call("_process_cancellation_with_userid", {"user_id": user_id})
            
            # Use the Airtable service to process cancellation
            cancellation_result = await airtable_service.process_cancellation(user_id)
            
            if cancellation_result["success"]:
                # Successful cancellation
                return f""" **Service Cancellation Confirmed**

Your service request with User ID: **{user_id}** has been successfully cancelled.

We're sorry to see you go! If you change your mind, feel free to book our services again anytime.

**Contact Information:**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}
🌐 Website: {self.basic_knowledge['website']}

Thank you for considering Adeona Technologies."""
            
            else:
                # Cancellation failed
                if cancellation_result.get("time_exceeded", False):
                    # 24-hour window exceeded
                    return f""" **Cancellation Not Possible**

Your service request (User ID: **{user_id}**) cannot be cancelled because it exceeds the **24-hour cancellation window**.

**What you can do:**
Please contact our support team directly to discuss your service request:

📞 **Phone: {self.basic_knowledge['phone']}**
📧 Email: {self.basic_knowledge['email']}

Our team will be happy to assist you with your concerns.

*Note: Services can only be cancelled within 24 hours of booking.*"""
                
                elif "not found" in cancellation_result["message"].lower():
                    # User ID not found
                    return f""" **User ID Not Found**

I couldn't find a service request with User ID: **{user_id}**

**Please check:**
• User ID is entered correctly (8 characters)
• User ID matches your booking confirmation

**Need Help?**
📞 Phone: {self.basic_knowledge['phone']}
📧 Email: {self.basic_knowledge['email']}

Our support team can help verify your booking details."""
                
                else:
                    # Other error
                    return f""" **Cancellation Error**

{cancellation_result['message']}

**For immediate assistance:**
📞 **Phone: {self.basic_knowledge['phone']}**
📧 Email: {self.basic_knowledge['email']}

Our support team will help resolve this issue."""
                    
        except Exception as e:
            log_error(e, "_process_cancellation_with_userid")
    
    # Continue with existing service booking methods and other functionality...
    async def _initiate_service_booking(self, session: SessionData) -> str:
        """Initiate service booking process"""
        session.user_data = ServiceRequest()
        session.user_data.step = "name"
        return f"""I'd be happy to help you book our services! 

Adeona Technologies offers {len(self.complete_services)} comprehensive IT solutions including:
• Custom Software Development
• Adeona Foresight CRM
• Mobile & Web Application Development  
• Digital Business Solutions
• And many more specialized services

To get started with your service request, please provide your full name."""
    
    # Include all other existing methods for booking, cancellation, audio generation, etc.
    # (keeping the existing implementations)
    
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
            return f"Please provide your name to start booking, or contact us at {self.basic_knowledge['phone']}."
    
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

**Name:** {user_data.name}
**Email:** {user_data.email}
**Phone:** {user_data.phone}
**Address:** {user_data.address}
**Service Details:** {user_data.service_details}

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
            return f"There was an error processing your request. Please try again or contact us at {self.basic_knowledge['phone']}."
                
        elif message_lower in ['edit', 'no', 'change']:
            user_data.step = "name"
            user_data.name = None
            user_data.email = None
            user_data.phone = None
            user_data.address = None
            user_data.service_details = None
            return "No problem! Let's start over. Please provide your full name."
        return "Please type 'confirm' to submit your request or 'edit' to make changes."
    
    async def _generate_audio_response(self, text: str) -> Optional[str]:
        """Generate audio response with enhanced error handling and rate limiting"""
        try:
            log_function_call("_generate_audio_response", {"text_length": len(text)})
            
            if not text or len(text.strip()) == 0:
                logger.warning("Empty text provided for TTS - skipping audio generation")
                return None
            
            # Limit text length for TTS
            max_tts_length = 500
            if len(text) > max_tts_length:
                text = text[:max_tts_length] + "..."
                logger.info(f"Text truncated to {max_tts_length} characters for TTS")
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"response_{timestamp}.wav"
            
            # Call TTS service with rate limiting handling
            try:
                audio_filename = await gemini_service.generate_speech(text, output_file=filename)
                
                if audio_filename:
                    audio_path = f"static/audio/{audio_filename}"
                    if os.path.exists(audio_path):
                        file_size = os.path.getsize(audio_path)
                        logger.info(f"Audio file verified: {audio_path} ({file_size} bytes)")
                        return audio_filename
                    else:
                        logger.error(f"Audio file not found at expected path: {audio_path}")
                        return None
                else:
                    logger.warning("TTS service returned None - audio generation failed")
                    return None
            
            except Exception as tts_error:
                error_str = str(tts_error)
                if "429" in error_str or "Too Many Requests" in error_str:
                    logger.warning("TTS rate limit exceeded - skipping audio generation")
                    return None
                elif "quota" in error_str.lower() or "limit" in error_str.lower():
                    logger.warning("TTS quota/limit exceeded - skipping audio generation")
                    return None
                else:
                    logger.error(f"TTS error: {error_str}")
                    return None
                
        except Exception as e:
            log_error(e, "_generate_audio_response")
            logger.error(f"Audio generation failed: {str(e)}")
            return None
    
    async def initialize_services(self):
        """Initialize required services with permanent local data loading"""
        try:
            log_function_call("initialize_services")
            
            # Initialize VectorDB (this will automatically load local data permanently)
            await vectordb_service.initialize()
            
            # Initialize other services
            await googlesheet_service.initialize()
            
            logger.info("Services initialized successfully with permanent local data storage")
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
                "mode": "Enhanced Local Data + VectorDB + SerpAPI Fallback",
                "services_available": len(self.complete_services),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            log_error(e, "get_session_stats")
            return {
                "active_sessions": 0, 
                "total_messages": 0, 
                "mode": "Enhanced Local Data + VectorDB", 
                "services_available": len(self.complete_services),
                "timestamp": datetime.now().isoformat()
            }
    
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

# Create global chatbot instance
adeona_chatbot = EnhancedAdeonaChatbot()