# App settings & environment configs

# Enhanced app settings with comprehensive Adeona Technologies data

import os
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables
load_dotenv()

class EnhancedAdeonaSettings:
    """Enhanced application configuration with comprehensive Adeona Technologies information"""
    
    # Gemini Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-pro"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
    EMBEDDING_DIMENSION: int = 768
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "adeona-website-content")
    
    # SerpAPI Configuration (STRICT Adeona-only)
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY")
    
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
    
    # STRICT Adeona Technologies Configuration
    ADEONA_DOMAIN: str = "adeonatech.net"
    WEBSITE_URL: str = "https://adeonatech.net"
    PRIVACY_POLICY_URL: str = "https://adeonatech.net/privacy-policy"
    
    # Verified Adeona pages ONLY
    TARGET_PAGES: List[str] = [
        "https://adeonatech.net/",
        "https://adeonatech.net/home",
        "https://adeonatech.net/about", 
        "https://adeonatech.net/service",
        "https://adeonatech.net/project",
        "https://adeonatech.net/contact",
        "https://adeonatech.net/privacy-policy"
    ]
    
    # Service Configuration
    CANCELLATION_HOURS: int = int(os.getenv("CANCELLATION_HOURS", "24"))
    
    # COMPREHENSIVE ADEONA TECHNOLOGIES INFORMATION
    COMPANY_INFO: Dict[str, str] = {
        "name": "Adeona Technologies",
        "founded_year": "2017",
        "country": "Sri Lanka",
        "city": "Colombo",
        "industry": "Information Technology Solutions",
        "specialization": "Custom Software Development and Digital Solutions",
        "website": "https://adeonatech.net/",
        "privacy_policy": "https://adeonatech.net/privacy-policy",
        "domain": "adeonatech.net"
    }
    
    # Contact Information
    CONTACT_INFO: Dict[str, str] = {
        "phone": "(+94) 117 433 3333",
        "email": "info@adeonatech.net",
        "address": "14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100",
        "contact_page": "https://adeonatech.net/contact"
    }
    
    # Complete Services List
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
    
    # Service Categories
    SERVICE_CATEGORIES: Dict[str, List[str]] = {
        "Software Development": [
            "Tailored Software Development",
            "API Design and Implementation",
            "Cross-Platform Mobile and Web Application Development",
            "Website Builder Tool"
        ],
        "Business Solutions": [
            "Adeona Foresight CRM",
            "Digital Business Card",
            "Inventory Management Solutions",
            "Restaurant Management System",
            "Lead Manager"
        ],
        "Digital Services": [
            "Digital Bill",
            "Value Added Service Development (VAS)",
            "In-App and In-Web Advertising Solutions",
            "Bulk SMS and Rich Messaging"
        ],
        "Enterprise Solutions": [
            "Fleet Management Solutions",
            "3CX Business Communication",
            "Scratch Card Solution"
        ]
    }
    
    # Social Media (from cached data)
    SOCIAL_MEDIA: Dict[str, str] = {
        "linkedin": "https://www.linkedin.com/company/adeona-technologies/",
        "twitter": "https://twitter.com/adeona_tech",
        "facebook": "https://web.facebook.com/adeonatech"
    }
    
    # Adeona Keywords for Validation
    ADEONA_KEYWORDS: List[str] = [
        "adeona", "technologies", "adeona technologies", 
        "adeonatech", "sri lanka it", "colombo software",
        "it solutions sri lanka", "software development sri lanka"
    ]
    
    # Basic Company Responses (for questions that don't need search)
    BASIC_RESPONSES: Dict[str, str] = {
        "bot_name": "I'm AdeonaBot, the AI assistant for Adeona Technologies.",
        "company_name": "Adeona Technologies",
        "founded": f"Adeona Technologies was founded in 2017.",
        "location": f"We are located in Colombo, Sri Lanka at: 14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100",
        "contact": f"Contact us: Phone: (+94) 117 433 3333, Email: info@adeonatech.net",
        "website": f"Visit our website: https://adeonatech.net/",
        "privacy": f"Our privacy policy: https://adeonatech.net/privacy-policy"
    }
    
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
            "SERPAPI_API_KEY",  # Required for Adeona content extraction
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
        
        # Special validation for SerpAPI (critical for Adeona content)
        if not cls.SERPAPI_API_KEY:
            raise ValueError("SERPAPI_API_KEY is required for Adeona content extraction. Get your key at https://serpapi.com/")
        
        print(f"✓ Configuration validated for {cls.COMPANY_INFO['name']}")
        print(f"✓ Target domain: {cls.ADEONA_DOMAIN}")
        print(f"✓ Services configured: {len(cls.COMPANY_SERVICES)}")
        
        return True
    
    @classmethod
    def get_company_overview(cls) -> str:
        """Get formatted company overview"""
        return f"""{cls.COMPANY_INFO['name']} is a leading {cls.COMPANY_INFO['industry']} company founded in {cls.COMPANY_INFO['founded_year']} and based in {cls.COMPANY_INFO['city']}, {cls.COMPANY_INFO['country']}.

We specialize in {cls.COMPANY_INFO['specialization']} and offer {len(cls.COMPANY_SERVICES)} different services including:
• Custom Software Development
• CRM Systems (Adeona Foresight CRM) 
• Mobile & Web Applications
• Digital Business Solutions

Website: {cls.COMPANY_INFO['website']}
Contact: {cls.CONTACT_INFO['phone']} | {cls.CONTACT_INFO['email']}"""
    
    @classmethod
    def get_services_by_category(cls, category: str = None) -> Dict[str, List[str]]:
        """Get services organized by category"""
        if category and category in cls.SERVICE_CATEGORIES:
            return {category: cls.SERVICE_CATEGORIES[category]}
        return cls.SERVICE_CATEGORIES
    
    @classmethod
    def is_adeona_url(cls, url: str) -> bool:
        """Check if URL belongs to Adeona Technologies"""
        return cls.ADEONA_DOMAIN.lower() in url.lower()
    
    @classmethod
    def get_contact_formatted(cls) -> str:
        """Get formatted contact information"""
        return f"""**Contact Adeona Technologies:**

Phone: {cls.CONTACT_INFO['phone']}
Email: {cls.CONTACT_INFO['email']}
Address: {cls.CONTACT_INFO['address']}
Website: {cls.COMPANY_INFO['website']}
Privacy Policy: {cls.COMPANY_INFO['privacy_policy']}

Social Media:
• LinkedIn: {cls.SOCIAL_MEDIA['linkedin']}
• Twitter: {cls.SOCIAL_MEDIA['twitter']}  
• Facebook: {cls.SOCIAL_MEDIA['facebook']}"""

# Create settings instance
settings = EnhancedAdeonaSettings()