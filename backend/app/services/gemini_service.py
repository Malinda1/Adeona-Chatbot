# Gemini API integration

import os
import requests
import wave
import base64
import json
from typing import List, Optional
from google import genai
from google.genai import types
from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error, log_function_call

class GeminiService:
    """Service for interacting with Google Gemini AI models"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.tts_model = settings.GEMINI_TTS_MODEL
    
    async def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate text response using Gemini model"""
        try:
            log_function_call("generate_response", {"prompt_length": len(prompt)})
            
            # Combine system prompt with context if provided
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\nUser Query: {prompt}"
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            
            logger.info(f"Generated response with {len(response.text)} characters")
            return response.text
            
        except Exception as e:
            log_error(e, "generate_response")
            return "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team at (+94) 117 433 3333."
    
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
    
    async def generate_speech(self, text: str, voice_name: str = None, output_file: str = "output.wav") -> str:
        """Generate speech from text using Gemini TTS"""
        try:
            log_function_call("generate_speech", {
                "text_length": len(text), 
                "voice": voice_name or settings.TTS_VOICE_NAME
            })
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.tts_model}:generateContent?key={settings.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": text}]}],
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
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            base64_audio_data = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
            audio_bytes = base64.b64decode(base64_audio_data)
            
            # Ensure audio directory exists
            os.makedirs("static/audio", exist_ok=True)
            file_path = f"static/audio/{output_file}"
            
            self.save_wav(file_path, audio_bytes)
            logger.info(f"Speech generated and saved to {file_path}")
            return file_path
            
        except Exception as e:
            log_error(e, "generate_speech")
            return None
    
    async def chat_with_context(self, user_message: str, system_prompt: str, context: Optional[str] = None) -> str:
        """Generate chat response with system prompt and context"""
        try:
            log_function_call("chat_with_context", {
                "user_message_length": len(user_message),
                "has_context": bool(context)
            })
            
            # Build the complete prompt
            messages = [system_prompt]
            
            if context:
                messages.append(f"Relevant Information:\n{context}")
            
            messages.append(f"User: {user_message}")
            messages.append("Assistant:")
            
            full_prompt = "\n\n".join(messages)
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            
            logger.info("Generated contextual chat response")
            return response.text
            
        except Exception as e:
            log_error(e, "chat_with_context")
            return "I apologize, but I'm experiencing technical difficulties. Please contact our support team at (+94) 117 433 3333 for immediate assistance."
    
    async def analyze_user_intent(self, message: str) -> dict:
        """Analyze user intent to determine appropriate response strategy"""
        try:
            log_function_call("analyze_user_intent", {"message_length": len(message)})
            
            intent_prompt = f"""Analyze the user's message and categorize their intent:

User Message: "{message}"

Classify into one of these categories:
1. COMPANY_INFO - Questions about company, services, general information
2. CONTACT_REQUEST - Wants contact information, social media, phone/email
3. SERVICE_BOOKING - Wants to book/order a service
4. CANCELLATION - Wants to cancel a service
5. GREETING - General greetings, hello messages
6. OTHER - Doesn't fit other categories

Respond with JSON format:
{{"intent": "CATEGORY", "confidence": 0.8, "key_entities": ["entity1", "entity2"]}}"""

            response = await self.generate_response(intent_prompt)
            
            # Try to parse JSON response
            try:
                import json
                intent_data = json.loads(response.strip())
                logger.info(f"Analyzed intent: {intent_data}")
                return intent_data
            except:
                # Fallback if JSON parsing fails
                if any(word in message.lower() for word in ['service', 'book', 'order', 'buy']):
                    return {"intent": "SERVICE_BOOKING", "confidence": 0.7}
                elif any(word in message.lower() for word in ['cancel', 'remove', 'delete']):
                    return {"intent": "CANCELLATION", "confidence": 0.7}
                elif any(word in message.lower() for word in ['contact', 'phone', 'email', 'address']):
                    return {"intent": "CONTACT_REQUEST", "confidence": 0.7}
                elif any(word in message.lower() for word in ['hello', 'hi', 'hey']):
                    return {"intent": "GREETING", "confidence": 0.8}
                else:
                    return {"intent": "COMPANY_INFO", "confidence": 0.6}
                    
        except Exception as e:
            log_error(e, "analyze_user_intent")
            return {"intent": "COMPANY_INFO", "confidence": 0.5}

# Create global instance
gemini_service = GeminiService()