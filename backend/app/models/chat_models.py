# Chat session models

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = datetime.now()

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    audio_url: Optional[str] = None
    session_id: str
    timestamp: datetime = datetime.now()
    sources: Optional[List[str]] = []

class CustomerData(BaseModel):
    """Customer data model for service bookings"""
    user_id: str = str(uuid.uuid4())
    name: str
    email: EmailStr
    phone: str
    address: str
    service_details: str
    date_created: datetime = datetime.now()
    status: str = "active"
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove spaces and special characters
        clean_phone = ''.join(filter(str.isdigit, v))
        if len(clean_phone) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()

class ServiceRequest(BaseModel):
    """Service request model"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    service_details: Optional[str] = None
    step: str = "name"  # Current step in the booking process
    
class ContactInfo(BaseModel):
    """Contact information model"""
    source_name: str
    source: str

class VectorSearchResult(BaseModel):
    """Vector search result model"""
    content: str
    score: float
    metadata: Dict[str, Any]

class ToolResponse(BaseModel):
    """Tool response model"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: str

class SessionData(BaseModel):
    """Session data model"""
    session_id: str
    user_data: Optional[ServiceRequest] = None
    conversation_history: List[Dict[str, str]] = []
    last_activity: datetime = datetime.now()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()

class CancellationRequest(BaseModel):
    """Cancellation request model"""
    user_id: str
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('User ID is required')
        return v.strip()

class WebsiteContent(BaseModel):
    """Website content model for vectorDB"""
    url: str
    title: str
    content: str
    page_type: str
    last_updated: datetime = datetime.now()
    
class EmbeddingData(BaseModel):
    """Embedding data model"""
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]