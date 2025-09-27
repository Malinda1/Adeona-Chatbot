# App settings & environment configs

# App settings & environment configs - SerpAPI only

import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

class Settings:
    """Application configuration settings - SerpAPI only for content extraction"""
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
    EMBEDDING_DIMENSION: int = 768
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "adeona-website-content")
    
    # SerpAPI Configuration (REQUIRED for content extraction)
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY")  # Add this to your .env file
    
    # Airtable Configuration
    AIRTABLE_API_KEY: str = os.getenv("AIRTABLE_API_KEY")
    AIRTABLE_BASE_ID: str = os.getenv("AIRTABLE_BASE_ID")
    AIRTABLE_TABLE_NAME: str = os.getenv("AIRTABLE_TABLE_NAME", "Customer_Data")
    
    # Google Sheets Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID")
    GOOGLE_SHEET_NAME: str = os.getenv("GOOGLE_SHEET_NAME", "Source_Details")
    
    # Application Configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Website Configuration - SerpAPI will extract from these pages
    WEBSITE_URL: str = "https://adeonatech.net"
    TARGET_PAGES: List[str] = [
        "https://adeonatech.net/home",
        "https://adeonatech.net/about", 
        "https://adeonatech.net/service",
        "https://adeonatech.net/project",
        "https://adeonatech.net/contact",
        "https://adeonatech.net/privacy-policy"
    ]
    
    # Legacy web scraping pages list (not used anymore - kept for compatibility)
    WEBSITE_PAGES: List[str] = [
        "/home",
        "/about",
        "/service",
        "/project",
        "/contact",
        "/privacy-policy"
    ]
    
    # Service Configuration
    CANCELLATION_HOURS: int = int(os.getenv("CANCELLATION_HOURS", "24"))
    
    # Company Services
    COMPANY_SERVICES: List[str] = [
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
        "Lead Manager"
    ]
    
    # Contact Information
    CONTACT_URL: str = f"{WEBSITE_URL}/contact"
    PHONE_NUMBER: str = "(+94) 117 433 3333"
    EMAIL: str = "info@adeonatech.net"
    
    # TTS Configuration
    TTS_VOICE_NAME: str = "Kore"
    TTS_SAMPLE_RATE: int = 24000
    TTS_CHANNELS: int = 1
    TTS_SAMPLE_WIDTH: int = 2
    
    @classmethod
    def validate_settings(cls):
        """Validate required environment variables"""
        required_vars = [
            "GEMINI_API_KEY",
            "PINECONE_API_KEY", 
            "SERPAPI_API_KEY",  # Now required for content extraction
            "AIRTABLE_API_KEY",
            "AIRTABLE_BASE_ID",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_SHEET_ID"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Special validation for SerpAPI
        if not cls.SERPAPI_API_KEY:
            print("WARNING: SERPAPI_API_KEY not found. Content extraction will be limited.")
            print("Get your SerpAPI key at https://serpapi.com/ and add it to your .env file:")
            print("SERPAPI_API_KEY=your_serpapi_key_here")
        
        return True

# Create settings instance
settings = Settings()