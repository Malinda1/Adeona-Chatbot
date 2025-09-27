# Adeona Chatbot

# Adeona Technologies Chatbot

An advanced, industrial-grade AI chatbot system for Adeona Technologies, providing comprehensive customer service, information retrieval, and service booking capabilities.

## Features

### Core Functionality
- **Multi-modal AI Responses**: Text and audio responses using Gemini AI
- **Website Content Extraction**: Automatic scraping and vectorization of company website
- **Service Booking System**: Complete customer onboarding with confirmation and cancellation
- **Contact Information Management**: Integration with Google Sheets for contact details
- **Vector Database Search**: Intelligent information retrieval using Pinecone
- **Professional Web Interface**: Responsive floating chatbot widget

### Business Logic
- **24-Hour Cancellation Policy**: Automated cancellation processing
- **Customer Data Management**: Secure storage in Airtable
- **Session Management**: Persistent conversation tracking
- **Intent Recognition**: Smart routing to appropriate handlers
- **Multi-step Service Booking**: Guided data collection process

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Models**: 
  - Gemini 2.5 Flash (Conversational AI)
  - Gemini Embedding-001 (Vector embeddings)
  - Gemini 2.5 Flash Preview TTS (Text-to-speech)
- **Vector Database**: Pinecone
- **Data Storage**: Airtable
- **External Integration**: Google Sheets API
- **Web Scraping**: BeautifulSoup + aiohttp

### Frontend
- **Technologies**: HTML5, CSS3, Vanilla JavaScript
- **Design**: Professional, mobile-responsive interface
- **Features**: Real-time chat, audio playback, typing indicators

## Project Structure

```
adeona-chatbot/
├── backend/
│   ├── app/
│   │   ├── config/          # Configuration and prompts
│   │   ├── core/            # Core chatbot logic
│   │   ├── services/        # External service integrations
│   │   ├── models/          # Data models
│   │   ├── utils/           # Utilities and logging
│   │   ├── main.py          # FastAPI application
│   │   └── routes.py        # API routes
│   ├── requirements.txt     # Python dependencies
│   ├── startup.py          # Initialization script
│   └── .env                # Environment variables
├── frontend/
│   ├── index.html          # Main webpage
│   └── static/
│       ├── css/style.css   # Styles
│       └── js/chatbot.js   # Chatbot functionality
├── data/                   # Data storage
└── README.md
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js (for development)
- Required API keys (see Environment Variables)

### 1. Clone Repository
```bash
git clone <repository-url>
cd adeona-chatbot
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### 3. Environment Variables
Create `.env` file in backend directory:

```bash
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=adeona-website-content

# Airtable Configuration
AIRTABLE_API_KEY=your_airtable_api_key_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
AIRTABLE_TABLE_NAME=Customer_Data

# Google Sheets Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_SHEET_NAME=Source_Details

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
WEBSITE_URL=https://adeonatech.net
```

### 4. Initialize Services
```bash
python startup.py
```

### 5. Start Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Chat API
- **POST** `/api/v1/chat` - Main chat endpoint
- **GET** `/api/v1/health` - Health check
- **GET** `/api/v1/stats` - System statistics

### Admin API
- **POST** `/api/v1/admin/reindex` - Reindex website content
- **POST** `/api/v1/admin/cleanup` - Clean old sessions

### Information API
- **GET** `/api/v1/contact` - Contact information
- **GET** `/api/v1/services` - Company services

## Configuration

### System Prompts
Located in `backend/app/config/prompts.py`:
- System prompt for AI personality
- Agent prompt for tool selection
- Context prompt for information retrieval
- Meta prompt for conversation management
- Function call prompt for decision making

### Service Settings
Located in `backend/app/config/settings.py`:
- API configurations
- Business rules (cancellation hours, services list)
- Website pages to scrape
- Contact information

## Data Models

### Customer Data (Airtable)
- UserID (8-character unique ID)
- Name, Email, Phone, Address
- Service Details
- Date Created, Status

### Contact Information (Google Sheets)
- Source Name (Phone, Email, Social Media)
- Source (Actual contact details/links)

### Vector Database (Pinecone)
- Website content chunks
- Embeddings for semantic search
- Metadata (URL, page type, chunk index)

## Deployment

### Render Deployment
The application is configured for Render deployment:

1. **Build Command**: `pip install -r backend/requirements.txt`
2. **Start Command**: `cd backend && python startup.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables**: Set all required env vars in Render dashboard

### Production Considerations
- Set `LOG_LEVEL=ERROR` in production
- Configure CORS origins properly
- Use production-grade secrets management
- Monitor API rate limits
- Set up health check monitoring

## Features Guide

### Service Booking Flow
1. User expresses interest in services
2. Bot collects: Name → Email → Phone → Address → Service Details
3. User confirms information
4. System generates unique User ID
5. Data saved to Airtable
6. Confirmation message with cancellation policy

### Cancellation Process
1. User provides User ID
2. System checks 24-hour window
3. If valid: deletes record and confirms
4. If expired: directs to contact support

### Information Retrieval
- **Website Content**: Searched via vector database
- **Contact Info**: Retrieved from Google Sheets
- **Services**: Listed from configuration

## Monitoring & Logging

### Logging System
- Comprehensive logging with rotation
- Error tracking with context
- Function call logging
- Performance monitoring

### Health Checks
- Service availability monitoring
- Database connection status
- API endpoint health verification

## Security Features

- Input validation and sanitization
- Session management
- Rate limiting considerations
- Secure API key management
- CORS configuration
- Data privacy compliance

## Customization

### Adding New Services
1. Update `COMPANY_SERVICES` in settings.py
2. Update website content if needed
3. Re-run website indexing

### Modifying Prompts
1. Edit prompts in `config/prompts.py`
2. Test with different scenarios
3. Restart application

### UI Customization
1. Modify CSS variables in `style.css`
2. Update HTML structure if needed
3. Adjust JavaScript functionality

## Troubleshooting

### Common Issues

**1. Vector Database Empty**
```bash
python startup.py  # Re-run initialization
```

**2. API Connection Errors**
- Check environment variables
- Verify API key permissions
- Check network connectivity

**3. Audio Not Playing**
- Browser audio policy restrictions
- Check file permissions
- Verify TTS service availability

### Logs Location
- Application logs: `backend/logs/`
- Error details in console output
- Health check status via `/health` endpoint

## Contributing

1. Follow the existing code structure
2. Add comprehensive logging
3. Update documentation
4. Test all functionality
5. Follow industrial coding standards

## License

Proprietary software for Adeona Technologies.

## Support

For technical support or questions:
- Email: info@adeonatech.net  
- Phone: (+94) 117 433 3333
- Website: https://adeonatech.net/contact
