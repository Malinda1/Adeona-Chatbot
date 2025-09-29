# Google Sheets integration


import os
import json
from typing import List, Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.app.config.settings import settings
from backend.app.models.chat_models import ContactInfo
from backend.app.utils.logger import logger, log_error, log_function_call

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

class GoogleSheetService:
    """Service for managing Google Sheets contact information"""
    
    def __init__(self):
        self.service = None
        self.sheet_id = settings.GOOGLE_SHEET_ID
        self.sheet_name = settings.GOOGLE_SHEET_NAME
        self._initialized = False
        
        # Contact information cache
        self.contact_data = {
            "Phone Number": "(+94) 117 433 333",
            "Email": "info@adeonatech.net",
            "Address": "14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100",
            "Linkedin Profile": "https://www.linkedin.com/company/adeona-technologies/",
            "X Profile": "https://twitter.com/adeona_tech",
            "Facebook Profile": "https://web.facebook.com/adeonatech"
        }
    
    async def initialize(self):
        """Initialize Google Sheets service"""
        try:
            log_function_call("initialize_googlesheets")
            
            # For now, we'll use the cached contact data
            # This can be expanded to actually connect to Google Sheets API
            self._initialized = True
            logger.info("Google Sheets service initialized with cached data")
            
        except Exception as e:
            log_error(e, "initialize_googlesheets")
            # Continue with cached data even if API fails
            self._initialized = True
    
    async def ensure_initialized(self):
        """Ensure the service is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def search_contact_info(self, query: str) -> List[ContactInfo]:
        """Search for contact information based on query"""
        try:
            await self.ensure_initialized()
            log_function_call("search_contact_info", {"query": query})
            
            query_lower = query.lower()
            results = []
            
            # Search for matching contact information
            for source_name, source_value in self.contact_data.items():
                source_lower = source_name.lower()
                
                # Check for matches
                if any(keyword in query_lower for keyword in [
                    'facebook', 'fb'
                ]) and 'facebook' in source_lower:
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'linkedin', 'linked in'
                ]) and 'linkedin' in source_lower:
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'twitter', 'x profile', 'x page'
                ]) and ('x profile' in source_lower or 'twitter' in source_lower):
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'phone', 'number', 'call', 'telephone'
                ]) and 'phone' in source_lower:
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'email', 'mail', 'e-mail'
                ]) and 'email' in source_lower:
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'address', 'location', 'where', 'office'
                ]) and 'address' in source_lower:
                    results.append(ContactInfo(source_name=source_name, source=source_value))
                
                elif any(keyword in query_lower for keyword in [
                    'social', 'social media', 'profiles'
                ]) and any(social in source_lower for social in ['facebook', 'linkedin', 'x profile']):
                    results.append(ContactInfo(source_name=source_name, source=source_value))
            
            # If no specific matches, return all contact info for general queries
            if not results and any(keyword in query_lower for keyword in [
                'contact', 'reach', 'get in touch', 'how to contact'
            ]):
                for source_name, source_value in self.contact_data.items():
                    results.append(ContactInfo(source_name=source_name, source=source_value))
            
            logger.info(f"Found {len(results)} contact info matches")
            return results
            
        except Exception as e:
            log_error(e, "search_contact_info")
            return []
    
    async def get_all_contact_info(self) -> List[ContactInfo]:
        """Get all available contact information"""
        try:
            await self.ensure_initialized()
            log_function_call("get_all_contact_info")
            
            results = []
            for source_name, source_value in self.contact_data.items():
                results.append(ContactInfo(source_name=source_name, source=source_value))
            
            return results
            
        except Exception as e:
            log_error(e, "get_all_contact_info")
            return []
    
    async def format_contact_response(self, contact_info: List[ContactInfo]) -> str:
        """Format contact information for response"""
        try:
            if not contact_info:
                return "No contact information found."
            
            formatted_parts = []
            for contact in contact_info:
                if contact.source.startswith('http'):
                    formatted_parts.append(f"**{contact.source_name}:** {contact.source}")
                else:
                    formatted_parts.append(f"**{contact.source_name}:** {contact.source}")
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            log_error(e, "format_contact_response")
            return "Error formatting contact information."
    
    async def get_facebook_page(self) -> Optional[str]:
        """Get Facebook page URL"""
        try:
            await self.ensure_initialized()
            return self.contact_data.get("Facebook Profile")
        except Exception as e:
            log_error(e, "get_facebook_page")
            return None
    
    async def get_linkedin_page(self) -> Optional[str]:
        """Get LinkedIn page URL"""
        try:
            await self.ensure_initialized()
            return self.contact_data.get("Linkedin Profile")
        except Exception as e:
            log_error(e, "get_linkedin_page")
            return None
    
    async def get_twitter_page(self) -> Optional[str]:
        """Get Twitter/X page URL"""
        try:
            await self.ensure_initialized()
            return self.contact_data.get("X Profile")
        except Exception as e:
            log_error(e, "get_twitter_page")
            return None

# Create global instance
googlesheet_service = GoogleSheetService()