# Gemini API integration

# Enhanced Gemini API integration with improved intent analysis and rate limiting - FIXED CANCELLATION

import os
import requests
import wave
import base64
import json
import time
import asyncio
import re
from typing import List, Optional
from google import genai
from google.genai import types
from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error, log_function_call

class EnhancedGeminiService:
    """Enhanced service for interacting with Google Gemini AI models with improved Adeona-specific responses"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.tts_model = settings.GEMINI_TTS_MODEL
        # Rate limiting for TTS
        self.last_tts_request = 0
        self.tts_request_interval = 2  # Minimum seconds between TTS requests
        self.tts_retry_count = 0
        self.max_tts_retries = 3
    
    async def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate text response using Gemini model with enhanced Adeona focus"""
        try:
            log_function_call("generate_response", {"prompt_length": len(prompt)})
            
            # Enhance prompt with Adeona-specific instructions
            enhanced_prompt = self._enhance_prompt_for_adeona(prompt, context)
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=enhanced_prompt
            )
            
            logger.info(f"Generated response with {len(response.text)} characters")
            return response.text
            
        except Exception as e:
            log_error(e, "generate_response")
            return "I apologize, but I'm experiencing technical difficulties. Please contact our support team at (+94) 117 433 3333."
    
    def _enhance_prompt_for_adeona(self, prompt: str, context: Optional[str] = None) -> str:
        """Enhanced prompt enhancement with better search result integration"""
        
        adeona_guidelines = """
        CRITICAL: You are AdeonaBot representing Adeona Technologies ONLY.
        
        COMPANY INFORMATION:
        - Company: Adeona Technologies
        - Website: https://adeonatech.net/
        - Privacy Policy: https://adeonatech.net/privacy-policy
        - Phone: (+94) 117 433 3333
        - Email: info@adeonatech.net
        - Founded: 2017, Colombo, Sri Lanka
        - Services: 21 comprehensive IT solutions
        
        RESPONSE RULES:
        - Use ONLY information about Adeona Technologies
        - If context/search results are provided, prioritize that information
        - Be specific and detailed when information is available
        - Acknowledge limitations when information is insufficient
        - Always maintain professional, helpful tone
        - Include contact information when relevant
        - Never make up or assume information
        
        SEARCH RESULT INTEGRATION:
        - When context contains search results, use them as primary source
        - Quote specific details from search results
        - Combine information from multiple results for comprehensive answers
        - If search results are incomplete, acknowledge and provide contact info
        
        """
        
        if context:
            enhanced_prompt = f"{adeona_guidelines}\nVERIFIED ADEONA TECHNOLOGIES INFORMATION:\n{context}\n\nUSER QUERY: {prompt}\n\nProvide accurate, comprehensive response using the verified information:"
        else:
            enhanced_prompt = f"{adeona_guidelines}\nUSER QUERY: {prompt}\n\nProvide accurate response about Adeona Technologies:"
        
        return enhanced_prompt
    
    async def analyze_user_intent(self, message: str) -> dict:
        """ENHANCED: More accurate user intent analysis with FIXED cancellation detection"""
        try:
            log_function_call("analyze_user_intent", {"message_length": len(message)})
            
            message_lower = message.lower().strip()
            
            # PRIORITY 1: ENHANCED cancellation detection (highest priority)
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
            
            # Check cancellation patterns first (highest priority)
            for pattern in cancellation_patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"CANCELLATION detected via pattern: {pattern}")
                    return {
                        "intent": "CANCELLATION", 
                        "confidence": 0.95, 
                        "reasoning": f"Cancellation pattern matched: {pattern}"
                    }
            
            # Also check for simple "cancel" with context
            if 'cancel' in message_lower and len(message.split()) <= 5:
                return {
                    "intent": "CANCELLATION", 
                    "confidence": 0.90, 
                    "reasoning": "Simple cancellation request detected"
                }
            
            # PRIORITY 2: Social media and contact request detection
            social_media_patterns = [
                r'\b(facebook|fb|facebook profile|facebook page|facebook account)\b',
                r'\b(twitter|x profile|twitter profile|twitter account|x account)\b',
                r'\b(linkedin|linkedin profile|linkedin page|linkedin account)\b',
                r'\b(instagram|insta|instagram profile|instagram account)\b',
                r'\b(social media|social profiles|social accounts)\b'
            ]
            
            contact_patterns = [
                r'\b(phone number|contact number|telephone|call)\b',
                r'\b(email address|email|contact email)\b',
                r'\b(contact.*info|contact.*details|how.*contact)\b',
                r'\b(reach you|get in touch|address|location)\b'
            ]
            
            # Check social media patterns
            for pattern in social_media_patterns:
                if re.search(pattern, message_lower):
                    return {
                        "intent": "SOCIAL_MEDIA_REQUEST",
                        "confidence": 0.90,
                        "reasoning": f"Social media request pattern: {pattern}"
                    }
            
            # Check general contact patterns
            for pattern in contact_patterns:
                if re.search(pattern, message_lower):
                    return {
                        "intent": "CONTACT_REQUEST", 
                        "confidence": 0.85, 
                        "reasoning": f"Contact request pattern: {pattern}"
                    }
            
            # PRIORITY 3: Service booking detection (AFTER cancellation check)
            booking_patterns = [
                # Direct booking phrases
                r'\b(book|order|purchase|buy|hire|request|get)\b.*\b(service|solution|software|crm|app|development)\b',
                r'\b(i want to|i need to|want to|need to)\b.*\b(book|order|get|hire|request)\b.*\b(service|solution)\b',
                r'\b(i want|i need|want|need)\b.*\b(your service|a service|booking)\b',
                
                # Service-specific requests
                r'\b(get|book|order|want|need)\b.*\b(crm|software development|mobile app|web development)\b',
                r'\b(i\'m interested in|interested in)\b.*\b(booking|hiring|purchasing)\b'
            ]
            
            # Only check booking patterns if it's not a cancellation request
            for pattern in booking_patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"SERVICE_BOOKING detected via pattern: {pattern}")
                    return {
                        "intent": "SERVICE_BOOKING", 
                        "confidence": 0.90, 
                        "reasoning": f"Booking pattern matched: {pattern}"
                    }
            
            # PRIORITY 4: Service inquiry detection
            service_inquiry_patterns = [
                r'\b(what services|what do you offer|what can you do|list.*services)\b',
                r'\b(what are your|what kind of|tell me about.*your)\b.*\b(services|solutions|offerings)\b',
                r'\b(services.*do you provide|solutions.*do you offer|what.*solutions)\b',
                r'\b(available services|service list|your capabilities)\b',
                r'\b(this company|your company|the company)\b.*\b(services|solutions|do|offer)\b'
            ]
            
            for pattern in service_inquiry_patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"SERVICE_INQUIRY detected via pattern: {pattern}")
                    return {
                        "intent": "SERVICE_INQUIRY",
                        "confidence": 0.85,
                        "reasoning": f"Service inquiry pattern: {pattern}"
                    }
            
            # PRIORITY 5: Simple greeting detection (restrictive)
            greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
            is_simple_greeting = (
                any(greeting in message_lower for greeting in greeting_words) and
                len(message.split()) <= 3 and
                not any(word in message_lower for word in [
                    'about', 'service', 'company', 'what', 'how', 'can', 'help', 
                    'tell', 'information', 'details', 'question', 'do you', 'are you'
                ])
            )
            
            if is_simple_greeting:
                return {
                    "intent": "GREETING", 
                    "confidence": 0.85, 
                    "reasoning": "Simple greeting without additional questions"
                }
            
            # PRIORITY 6: Privacy policy detection
            privacy_patterns = [
                r'\b(privacy policy|data protection|personal information)\b',
                r'\b(privacy.*practices|data.*security|information.*collection)\b',
                r'\b(how.*data|what.*data|privacy)\b'
            ]
            
            for pattern in privacy_patterns:
                if re.search(pattern, message_lower):
                    return {
                        "intent": "PRIVACY_INQUIRY",
                        "confidence": 0.85,
                        "reasoning": f"Privacy inquiry pattern: {pattern}"
                    }
            
            # Default to COMPANY_INFO for all other queries (ensures VectorDB search)
            return {
                "intent": "COMPANY_INFO", 
                "confidence": 0.80, 
                "reasoning": "General inquiry about Adeona Technologies - will use enhanced search"
            }
                    
        except Exception as e:
            log_error(e, "analyze_user_intent")
            return {
                "intent": "COMPANY_INFO", 
                "confidence": 0.5, 
                "reasoning": "Error in analysis, defaulting to company info search"
            }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini embedding model"""
        try:
            log_function_call("generate_embedding", {"text_length": len(text)})
            
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=settings.EMBEDDING_DIMENSION)
            )
            
            embedding_vector = response.embeddings[0].values
            logger.info(f"Generated embedding with dimension: {len(embedding_vector)}")
            return embedding_vector
            
        except Exception as e:
            log_error(e, "generate_embedding")
            raise e
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            log_function_call("generate_batch_embeddings", {"count": len(texts)})
            
            embeddings = []
            for text in texts:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            log_error(e, "generate_batch_embeddings")
            raise e
    
    def save_wav(self, file_path: str, audio_data: bytes):
        """Save raw PCM audio data to a WAV file"""
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(settings.TTS_CHANNELS)
                wf.setsampwidth(settings.TTS_SAMPLE_WIDTH)
                wf.setframerate(settings.TTS_SAMPLE_RATE)
                wf.writeframes(audio_data)
            logger.info(f"Audio saved to {file_path}")
        except Exception as e:
            log_error(e, "save_wav")
            raise e
    
    async def _wait_for_rate_limit(self):
        """Wait for rate limiting if necessary"""
        current_time = time.time()
        elapsed = current_time - self.last_tts_request
        
        if elapsed < self.tts_request_interval:
            wait_time = self.tts_request_interval - elapsed
            logger.info(f"Rate limiting TTS request - waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
    
    async def generate_speech(self, text: str, voice_name: str = None, output_file: str = "output.wav") -> Optional[str]:
        """Generate speech from text using Gemini TTS with text chunking for long responses"""
        try:
            log_function_call("generate_speech", {
                "text_length": len(text), 
                "voice": voice_name or settings.TTS_VOICE_NAME,
                "output_file": output_file
            })
            
            # Clean and prepare text
            clean_text = self._clean_text_for_tts(text)
            
            # If text is too long, truncate intelligently
            max_tts_length = 800  # Increased from 500
            if len(clean_text) > max_tts_length:
                clean_text = self._truncate_text_intelligently(clean_text, max_tts_length)
                logger.info(f"Text truncated to {len(clean_text)} characters for TTS")
            
            # Rate limiting
            await self._wait_for_rate_limit()
            
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.tts_model}:generateContent?key={settings.GEMINI_API_KEY}"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "contents": [{"parts": [{"text": clean_text}]}],
                        "generationConfig": {
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {
                                "voiceConfig": {
                                    "prebuiltVoiceConfig": {
                                        "voiceName": voice_name or settings.TTS_VOICE_NAME
                                    }
                                }
                            }
                        }
                    }
                    
                    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                    
                    # Update last request time
                    self.last_tts_request = time.time()
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_count += 1
                        wait_time = 2 ** retry_count
                        logger.warning(f"TTS rate limit hit (attempt {retry_count}), waiting {wait_time} seconds...")
                        
                        if retry_count < max_retries:
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error("TTS rate limit exceeded after all retries")
                            return None
                    
                    elif response.status_code == 403:
                        logger.error("TTS quota exceeded")
                        return None
                    
                    elif not response.ok:
                        logger.error(f"TTS API error: {response.status_code} - {response.text}")
                        return None
                    
                    # Success - process the response
                    result = response.json()
                    
                    if 'candidates' not in result or not result['candidates']:
                        logger.error("No candidates in TTS response")
                        return None
                    
                    candidate = result['candidates'][0]
                    if 'content' not in candidate or 'parts' not in candidate['content']:
                        logger.error("Invalid TTS response structure")
                        return None
                    
                    parts = candidate['content']['parts']
                    if not parts or 'inlineData' not in parts[0]:
                        logger.error("No audio data in TTS response")
                        return None
                    
                    base64_audio_data = parts[0]['inlineData']['data']
                    audio_bytes = base64.b64decode(base64_audio_data)
                    
                    # Create directory and save file
                    audio_dir = "static/audio"
                    os.makedirs(audio_dir, exist_ok=True)
                    full_file_path = os.path.join(audio_dir, output_file)
                    
                    # Save the audio file
                    self.save_wav(full_file_path, audio_bytes)
                    
                    # Verify file was created
                    if os.path.exists(full_file_path):
                        file_size = os.path.getsize(full_file_path)
                        logger.info(f"Speech generated: {full_file_path} ({file_size} bytes) for {len(clean_text)} chars")
                        return output_file
                    else:
                        logger.error(f"Audio file was not created at {full_file_path}")
                        return None
                
                except requests.exceptions.Timeout:
                    retry_count += 1
                    logger.warning(f"TTS request timeout (attempt {retry_count})")
                    if retry_count < max_retries:
                        await asyncio.sleep(2)
                        continue
                    return None
                
                except requests.exceptions.RequestException as e:
                    logger.error(f"TTS request error: {str(e)}")
                    return None
                
                except Exception as e:
                    retry_count += 1
                    logger.error(f"TTS processing error (attempt {retry_count}): {str(e)}")
                    if retry_count < max_retries:
                        await asyncio.sleep(2)
                        continue
                    return None
            
            logger.error("TTS generation failed after all retry attempts")
            return None
            
        except Exception as e:
            log_error(e, "generate_speech")
            logger.error(f"TTS Error details: {str(e)}")
            return None
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS - remove formatting, special characters"""
        import re
        
        # Remove markdown formatting
        clean = re.sub(r'\*\*\*', '', text)  # Remove triple asterisks
        clean = re.sub(r'\*\*', '', clean)   # Remove double asterisks
        clean = re.sub(r'\* ', '', clean)    # Remove bullet asterisks
        clean = re.sub(r'`', '', clean)      # Remove backticks
        clean = re.sub(r'#+ ', '', clean)    # Remove markdown headers
        
        # Remove URLs (they don't speak well)
        clean = re.sub(r'https?://[^\s]+', '', clean)
        
        # Remove special unicode characters
        clean = re.sub(r'[✓✗✅❌📞📧🌐•]', '', clean)
        
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', clean)
        
        # Remove newlines (replace with periods for better speech flow)
        clean = re.sub(r'\n+', '. ', clean)
        
        return clean.strip()
    
    def _truncate_text_intelligently(self, text: str, max_length: int) -> str:
        """Intelligently truncate text at sentence boundaries"""
        if len(text) <= max_length:
            return text
        
        # Try to truncate at sentence end
        truncated = text[:max_length]
        
        # Find the last sentence end
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')
        
        # Use the last sentence boundary found
        last_sentence = max(last_period, last_question, last_exclamation)
        
        if last_sentence > max_length * 0.7:  # If we found a sentence end in the last 30%
            return truncated[:last_sentence + 1].strip()
        
        # Otherwise, truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space].strip() + "..."
        
        return truncated.strip() + "..."
    
    async def chat_with_context(self, user_message: str, system_prompt: str, context: Optional[str] = None) -> str:
        """ENHANCED: Generate chat response with system prompt and context, optimized for Adeona"""
        try:
            log_function_call("chat_with_context", {
                "user_message_length": len(user_message),
                "has_context": bool(context)
            })
            
            # Build enhanced Adeona-focused prompt
            adeona_system = f"""
            {system_prompt}
            
            CRITICAL INSTRUCTIONS for AdeonaBot:
            - You represent ONLY Adeona Technologies (https://adeonatech.net/)
            - Founded 2017, Colombo, Sri Lanka
            - 21 comprehensive services available
            - Contact: (+94) 117 433 3333 | info@adeonatech.net
            - Privacy Policy: https://adeonatech.net/privacy-policy
            
            RESPONSE APPROACH:
            - Use provided context as primary information source
            - Be comprehensive when context provides sufficient detail
            - Acknowledge limitations when context is insufficient
            - Always relate responses specifically to Adeona Technologies
            - Include contact information when relevant
            """
            
            messages = [adeona_system]
            
            if context:
                messages.append(f"VERIFIED ADEONA TECHNOLOGIES CONTEXT:\n{context}")
            
            messages.append(f"USER QUESTION: {user_message}")
            messages.append("AdeonaBot Response (comprehensive and accurate):")
            
            full_prompt = "\n\n".join(messages)
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            
            logger.info("Generated enhanced contextual Adeona-focused response")
            return response.text
            
        except Exception as e:
            log_error(e, "chat_with_context")
            return "I apologize, but I'm experiencing technical difficulties. Please contact our support team at (+94) 117 433 3333 for immediate assistance."
    
    async def generate_service_response(self, query: str, search_results: List, complete_services: List[str]) -> str:
        """ENHANCED: Generate comprehensive service-focused response"""
        try:
            log_function_call("generate_service_response", {"query": query[:50]})
            
            # Prepare context from search results
            context = ""
            if search_results:
                context_parts = []
                for result in search_results[:5]:  # Use top 5 results
                    content = result.content.strip()
                    if len(content) > 300:
                        content = content[:300] + "..."
                    context_parts.append(content)
                context = "\n\n".join(context_parts)
            
            service_prompt = f"""You are AdeonaBot providing comprehensive information about Adeona Technologies services.

CONTEXT FROM SEARCH RESULTS:
{context if context else "Limited search context available"}

COMPLETE ADEONA TECHNOLOGIES SERVICES (21 total):
{', '.join(complete_services)}

USER QUESTION: {query}

INSTRUCTIONS:
- Provide comprehensive service information using search context when available
- List relevant services based on the user's question
- Group services logically (development, CRM, communication, etc.)
- Include brief descriptions using search result information
- Mention total count: "Adeona Technologies offers 21 comprehensive services"
- End with contact information for detailed discussions
- If search context is limited, use the complete service list

RESPONSE FORMAT:
- Start with direct answer to user's question
- List relevant services with descriptions
- Include service categories if helpful
- End with contact information and next steps

Generate comprehensive, helpful response:"""

            response = await self.generate_response(service_prompt)
            return response
            
        except Exception as e:
            log_error(e, "generate_service_response")
            return f"""Adeona Technologies offers 21 comprehensive IT solutions including:

**Core Services:**
• Custom Software Development
• Adeona Foresight CRM  
• Mobile & Web Application Development
• Digital Business Solutions

**Complete Service List:**
{', '.join(complete_services)}

For detailed service information:
📞 Phone: (+94) 117 433 3333
📧 Email: info@adeonatech.net
🌐 Website: https://adeonatech.net/

Would you like to book a consultation or learn more about specific services?"""

# Create global instance
gemini_service = EnhancedGeminiService()