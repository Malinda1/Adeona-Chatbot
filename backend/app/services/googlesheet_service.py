# Google Sheets integration

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Any
import json
import os
from backend.app.config.settings import settings
from backend.app.models.chat_models import ContactInfo
from backend.app.utils.logger import logger, log_error, log_function_call

class GoogleSheetService:
    """Service for managing Google Sheets integration for contact information"""
    
    def __init__(self):
        self.sheet_id = settings.GOOGLE_SHEET_ID
        self.sheet_name = settings.GOOGLE_SHEET_NAME
        self.client = None
        self.worksheet = None
        self._initialized = False
    
    def _get_credentials(self):
        """Get Google Sheets credentials from environment variables"""
        try:
            # Create credentials from environment variables
            creds_info = {
                "type": "service_account",
                "project_id": "your-project-id",  # You'll need to add this to settings
                "private_key_id": "key-id",
                "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("GOOGLE_CLIENT_EMAIL", ""),
                "client_id": settings.GOOGLE_CLIENT_ID,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL', '')}"
            }
            
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            return Credentials.from_service_account_info(creds_info, scopes=scope)
            
        except Exception as e:
            log_error(e, "_get_credentials")
            # Fallback: try to use OAuth2 with client ID and secret
            return None
    
    async def initialize(self):
        """Initialize Google Sheets client"""
        try:
            log_function_call("initialize_googlesheets")
            
            credentials = self._get_credentials()
            if not credentials:
                # Fallback initialization without service account
                logger.warning("Using simplified Google Sheets access")
                self.client = gspread.service_account()
            else:
                self.client = gspread.authorize(credentials)
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.sheet_id)
            self.worksheet = spreadsheet.worksheet(self.sheet_name)
            
            self._initialized = True
            logger.info("Google Sheets service initialized successfully")
            
        except Exception as e:
            log_error(e, "initialize_googlesheets")
            # Create a mock service for development
            logger.warning("Using mock Google Sheets service")
            self._initialized = True
            self._create_mock_data()
    
    def _create_mock_data(self):
        """Create mock data for testing when Google Sheets is not available"""
        self.mock_data = [
            {"Source Name": "Phone Number", "Source": "(+94) 117 433 3333"},
            {"Source Name": "Email", "Source": "info@adeonatech.net"},
            {"Source Name": "Linkedin Profile", "Source": "https://www.linkedin.com/company/adeona-technologies/"},
            {"Source Name": "X Profile", "Source": "https://twitter.com/adeona_tech"},
            {"Source Name": "Address", "Source": "14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100"},
            {"Source Name": "Facebook Profile", "Source": "https://web.facebook.com/adeonatech"}
        ]
    
    async def ensure_initialized(self):
        """Ensure the Google Sheets service is initialized"""
        if not self._initialized:
            await self.initialize()
    
    async def get_all_contact_info(self) -> List[ContactInfo]:
        """Get all contact information from Google Sheet"""
        try:
            await self.ensure_initialized()
            log_function_call("get_all_contact_info")
            
            if not self.worksheet:
                # Use mock data
                contact_info = []
                for row in self.mock_data:
                    contact_info.append(ContactInfo(
                        source_name=row["Source Name"],
                        source=row["Source"]
                    ))
                logger.info(f"Retrieved {len(contact_info)} contact info entries (mock data)")
                return contact_info
            
            # Get all records from the sheet
            records = self.worksheet.get_all_records()
            
            contact_info = []
            for record in records:
                if record.get("Source Name") and record.get("Source"):
                    contact_info.append(ContactInfo(
                        source_name=record["Source Name"],
                        source=record["Source"]
                    ))
            
            logger.info(f"Retrieved {len(contact_info)} contact info entries")
            return contact_info
            
        except Exception as e:
            log_error(e, "get_all_contact_info")
            return []
    
    async def search_contact_info(self, query: str) -> List[ContactInfo]:
        """Search for specific contact information"""
        try:
            await self.ensure_initialized()
            log_function_call("search_contact_info", {"query": query})
            
            all_contacts = await self.get_all_contact_info()
            
            # Filter contacts based on query
            query_lower = query.lower()
            matching_contacts = []
            
            for contact in all_contacts:
                if (query_lower in contact.source_name.lower() or 
                    query_lower in contact.source.lower()):
                    matching_contacts.append(contact)
            
            # Special handling for common queries
            if not matching_contacts:
                if any(word in query_lower for word in ['phone', 'call', 'number']):
                    phone_contacts = [c for c in all_contacts if 'phone' in c.source_name.lower()]
                    matching_contacts.extend(phone_contacts)
                
                elif any(word in query_lower for word in ['email', 'mail']):
                    email_contacts = [c for c in all_contacts if 'email' in c.source_name.lower()]
                    matching_contacts.extend(email_contacts)
                
                elif any(word in query_lower for word in ['social', 'facebook', 'linkedin', 'twitter']):
                    social_contacts = [c for c in all_contacts if any(social in c.source_name.lower() 
                                     for social in ['facebook', 'linkedin', 'twitter', 'x profile'])]
                    matching_contacts.extend(social_contacts)
                
                elif any(word in query_lower for word in ['address', 'location', 'office']):
                    address_contacts = [c for c in all_contacts if 'address' in c.source_name.lower()]
                    matching_contacts.extend(address_contacts)
            
            logger.info(f"Found {len(matching_contacts)} matching contact entries")
            return matching_contacts
            
        except Exception as e:
            log_error(e, "search_contact_info")
            return []
    
    async def get_contact_by_type(self, contact_type: str) -> Optional[ContactInfo]:
        """Get specific contact information by type"""
        try:
            await self.ensure_initialized()
            log_function_call("get_contact_by_type", {"contact_type": contact_type})
            
            all_contacts = await self.get_all_contact_info()
            
            # Normalize the contact type
            contact_type_lower = contact_type.lower()
            
            for contact in all_contacts:
                if contact_type_lower in contact.source_name.lower():
                    logger.info(f"Found contact for type: {contact_type}")
                    return contact
            
            logger.info(f"No contact found for type: {contact_type}")
            return None
            
        except Exception as e:
            log_error(e, "get_contact_by_type")
            return None
    
    async def get_social_media_links(self) -> List[ContactInfo]:
        """Get all social media links"""
        try:
            await self.ensure_initialized()
            log_function_call("get_social_media_links")
            
            all_contacts = await self.get_all_contact_info()
            
            social_keywords = ['facebook', 'linkedin', 'twitter', 'x profile', 'instagram', 'youtube']
            social_contacts = []
            
            for contact in all_contacts:
                if any(keyword in contact.source_name.lower() for keyword in social_keywords):
                    social_contacts.append(contact)
            
            logger.info(f"Found {len(social_contacts)} social media links")
            return social_contacts
            
        except Exception as e:
            log_error(e, "get_social_media_links")
            return []
    
    async def format_contact_response(self, contacts: List[ContactInfo]) -> str:
        """Format contact information for response"""
        try:
            if not contacts:
                return "I couldn't find the specific contact information you're looking for. You can reach Adeona Technologies through our main contact page: https://adeonatech.net/contact"
            
            response_parts = []
            
            for contact in contacts:
                if contact.source_name.lower() == "phone number":
                    response_parts.append(f"Phone: {contact.source}")
                elif contact.source_name.lower() == "email":
                    response_parts.append(f"Email: {contact.source}")
                elif "address" in contact.source_name.lower():
                    response_parts.append(f"Address: {contact.source}")
                elif any(social in contact.source_name.lower() for social in ['facebook', 'linkedin', 'twitter', 'x profile']):
                    response_parts.append(f"{contact.source_name}: {contact.source}")
                else:
                    response_parts.append(f"{contact.source_name}: {contact.source}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            log_error(e, "format_contact_response")
            return "Error formatting contact information"
    
    async def update_contact_info(self, source_name: str, source: str) -> bool:
        """Update or add contact information (admin function)"""
        try:
            await self.ensure_initialized()
            log_function_call("update_contact_info", {"source_name": source_name})
            
            if not self.worksheet:
                logger.warning("Cannot update contact info - using mock data")
                return False
            
            # Find existing row or add new one
            all_records = self.worksheet.get_all_records()
            
            row_index = None
            for i, record in enumerate(all_records):
                if record.get("Source Name", "").lower() == source_name.lower():
                    row_index = i + 2  # +2 because sheets are 1-indexed and we skip header
                    break
            
            if row_index:
                # Update existing row
                self.worksheet.update(f'B{row_index}', source)
            else:
                # Add new row
                self.worksheet.append_row([source_name, source])
            
            logger.info(f"Contact info updated: {source_name}")
            return True
            
        except Exception as e:
            log_error(e, "update_contact_info")
            return False

# Create global instance
googlesheet_service = GoogleSheetService()