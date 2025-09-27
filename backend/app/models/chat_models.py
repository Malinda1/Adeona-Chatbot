# Chat session models

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

class ServiceRequest:
    """Service booking request data - Non-Pydantic for flexibility"""
    def __init__(self):
        self.step: str = "name"  # Current step in booking process
        self.name: Optional[str] = None
        self.email: Optional[str] = None
        self.phone: Optional[str] = None
        self.address: Optional[str] = None
        self.service_details: Optional[str] = None

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

class ConversationMessage:
    """Individual conversation message - Non-Pydantic for flexibility"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.timestamp = datetime.now()

class SessionData:
    """Session data for tracking user conversations - Non-Pydantic for flexibility"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history: List[ConversationMessage] = []
        self.user_data: Optional[ServiceRequest] = None
        self.last_activity = datetime.now()
        # Add cancellation tracking - not needed anymore with new approach
        # but kept for compatibility
        self.awaiting_cancellation_id: bool = False
        self.cancellation_step: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        message = ConversationMessage(role, content)
        self.conversation_history.append(message)
        self.last_activity = datetime.now()
    
    def get_recent_messages(self, count: int = 5) -> List[ConversationMessage]:
        """Get recent messages from conversation"""
        return self.conversation_history[-count:] if self.conversation_history else []

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