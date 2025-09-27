# Fixed SerpAPI service with SSL certificate handling

# SerpAPI service for comprehensive website content extraction

import os
import asyncio
import aiohttp
import ssl
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import json
from datetime import datetime

from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error, log_function_call
from backend.app.models.chat_models import WebsiteContent

class SerpAPIService:
    """Service for extracting comprehensive website content using SerpAPI only"""
    
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.base_url = "https://serpapi.com/search"
        self.website_url = "https://adeonatech.net"
        self.target_pages = [
            "https://adeonatech.net/home",
            "https://adeonatech.net/about", 
            "https://adeonatech.net/service",
            "https://adeonatech.net/project",
            "https://adeonatech.net/contact",
            "https://adeonatech.net/privacy-policy"
        ]
        
    async def extract_page_content_via_serpapi(self, url: str) -> Optional[WebsiteContent]:
        """Extract page content using SerpAPI's Google search with site: operator"""
        try:
            log_function_call("extract_page_content_via_serpapi", {"url": url})
            
            if not self.serpapi_key:
                logger.error("SerpAPI key not provided")
                return None
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Extract the specific page path from URL
            page_path = urlparse(url).path
            if page_path == '/':
                page_path = '/home'
            
            # Use Google search with site: operator to find specific page
            search_queries = [
                f'site:adeonatech.net{page_path}',
                f'site:adeonatech.net "{page_path.replace("/", "")}"',
                f'site:adeonatech.net intitle:"{page_path.replace("/", "")}"'
            ]
            
            best_content = None
            max_content_length = 0
            
            try:
                async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30)) as session:
                    
                    for query in search_queries:
                        try:
                            params = {
                                'api_key': self.serpapi_key,
                                'engine': 'google',
                                'q': query,
                                'num': 3,  # Get top 3 results
                                'hl': 'en',
                                'gl': 'us'
                            }
                            
                            logger.info(f"Searching with query: {query}")
                            
                            async with session.get(self.base_url, params=params) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    
                                    if 'organic_results' in data and data['organic_results']:
                                        for result in data['organic_results']:
                                            # Check if this result is actually from the target URL
                                            result_url = result.get('link', '')
                                            if url.lower() in result_url.lower() or page_path in result_url:
                                                
                                                title = result.get('title', 'Adeona Technologies')
                                                snippet = result.get('snippet', '')
                                                
                                                # Try to get more content from rich snippets
                                                rich_snippet = result.get('rich_snippet', {})
                                                rich_content = ""
                                                
                                                if isinstance(rich_snippet, dict):
                                                    if 'top' in rich_snippet:
                                                        rich_content += str(rich_snippet['top']) + " "
                                                    if 'bottom' in rich_snippet:
                                                        rich_content += str(rich_snippet['bottom']) + " "
                                                
                                                # Combine all available content
                                                full_content = f"{snippet} {rich_content}".strip()
                                                
                                                # Check for sitelinks (additional page content)
                                                sitelinks = result.get('sitelinks', [])
                                                sitelink_content = ""
                                                if sitelinks:
                                                    for sitelink in sitelinks:
                                                        if isinstance(sitelink, dict):
                                                            sitelink_title = sitelink.get('title', '')
                                                            sitelink_snippet = sitelink.get('snippet', '')
                                                            if sitelink_title or sitelink_snippet:
                                                                sitelink_content += f"{sitelink_title}: {sitelink_snippet} "
                                                
                                                if sitelink_content:
                                                    full_content += f" Additional Information: {sitelink_content}"
                                                
                                                # Check for featured snippet
                                                if 'featured_snippet' in data:
                                                    featured = data['featured_snippet']
                                                    if isinstance(featured, dict):
                                                        featured_snippet = featured.get('snippet', '')
                                                        if featured_snippet:
                                                            full_content = f"Featured Content: {featured_snippet} {full_content}"
                                                
                                                if len(full_content) > max_content_length:
                                                    max_content_length = len(full_content)
                                                    page_type = self._determine_page_type(url)
                                                    
                                                    best_content = WebsiteContent(
                                                        url=url,
                                                        title=title,
                                                        content=self._clean_and_enhance_content(full_content, page_type),
                                                        page_type=page_type
                                                    )
                                                
                                                logger.info(f"Found content for {url}: {len(full_content)} chars from query: {query}")
                                                break
                                        
                                        if best_content and len(best_content.content) > 200:
                                            break  # We found good content, no need to try more queries
                                
                                else:
                                    logger.warning(f"SerpAPI request failed: {response.status}")
                                
                            # Wait between API calls to respect rate limits
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            logger.warning(f"Query failed: {query} - {e}")
                            continue
                
                if best_content:
                    return best_content
                else:
                    # If no content found, create a basic structure with page type info
                    logger.warning(f"No substantial content found for {url}, creating basic entry")
                    page_type = self._determine_page_type(url)
                    basic_content = self._get_default_content_for_page_type(page_type)
                    
                    return WebsiteContent(
                        url=url,
                        title=f"Adeona Technologies - {page_type.title()}",
                        content=basic_content,
                        page_type=page_type
                    )
                    
            except Exception as e:
                log_error(e, f"SerpAPI extraction failed for {url}")
                return None
                        
        except Exception as e:
            log_error(e, f"extract_page_content_via_serpapi for {url}")
            return None
    
    def _clean_and_enhance_content(self, content: str, page_type: str) -> str:
        """Clean and enhance extracted content with page-specific information"""
        if not content:
            return self._get_default_content_for_page_type(page_type)
        
        # Clean the content
        cleaned = self._clean_text(content)
        
        # Add page-specific context
        context_info = self._get_context_for_page_type(page_type)
        
        # Combine cleaned content with context
        enhanced_content = f"{context_info}\n\n{cleaned}" if context_info else cleaned
        
        return enhanced_content
    
    def _get_context_for_page_type(self, page_type: str) -> str:
        """Get contextual information for specific page types"""
        context_map = {
            'home': "Adeona Technologies - Leading IT Solutions Company in Sri Lanka",
            'about': "About Adeona Technologies - Company Information and Background",
            'services': "Adeona Technologies Services - IT Solutions and Software Development",
            'projects': "Adeona Technologies Projects - Portfolio and Case Studies", 
            'contact': "Contact Adeona Technologies - Get in Touch with Our Team",
            'privacy': "Adeona Technologies Privacy Policy - Data Protection and Privacy Practices"
        }
        return context_map.get(page_type, f"Adeona Technologies - {page_type.title()} Information")
    
    def _get_default_content_for_page_type(self, page_type: str) -> str:
        """Provide default content when extraction fails"""
        default_content = {
            'home': """Adeona Technologies is a leading IT solutions company based in Sri Lanka, specializing in custom software development and innovative digital solutions. We provide comprehensive IT services including Tailored Software Development, Adeona Foresight CRM, Mobile and Web Application Development, API Design and Implementation, and various other technology solutions to help businesses grow and succeed in the digital age.""",
            
            'about': """Adeona Technologies is an innovative IT solutions company committed to delivering cutting-edge software development and digital transformation services. Our team of experienced professionals specializes in creating tailored solutions that meet the unique needs of businesses across various industries. We pride ourselves on our technical expertise, customer-centric approach, and commitment to excellence in everything we do.""",
            
            'services': """Adeona Technologies offers a comprehensive range of IT services including: Tailored Software Development, Adeona Foresight CRM, Digital Bill, Digital Business Card, Value Added Service Development (VAS), Cross-Platform Mobile and Web Application Development, In-App and In-Web Advertising Solutions, API Design and Implementation, Inventory Management Solutions, Bulk SMS and Rich Messaging, Fleet Management Solutions, Website Builder Tool, Restaurant Management System, 3CX Business Communication, Scratch Card Solution, and Lead Manager.""",
            
            'projects': """Adeona Technologies has successfully delivered numerous projects across various industries, showcasing our expertise in software development, mobile applications, web solutions, and enterprise systems. Our portfolio includes CRM systems, mobile applications, e-commerce platforms, inventory management solutions, and custom software applications tailored to meet specific business requirements.""",
            
            'contact': """Contact Adeona Technologies: Phone: (+94) 117 433 3333, Email: info@adeonatech.net, Address: 14, Sir Baron Jayathilaka Mawatha, Colombo, Sri Lanka, 00100. Visit our contact page at https://adeonatech.net/contact for more information and to get in touch with our team.""",
            
            'privacy': """Adeona Technologies Privacy Policy: We are committed to protecting your privacy and ensuring the security of your personal information. Our privacy policy outlines how we collect, use, store, and protect your data in compliance with applicable data protection regulations. We implement industry-standard security measures to safeguard your information and maintain strict confidentiality in all our business operations. For detailed information about our data handling practices, privacy rights, and security measures, please refer to our complete privacy policy on our website."""
        }
        
        return default_content.get(page_type, f"Information about Adeona Technologies {page_type} section.")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        # Replace special unicode characters
        replacements = {
            '\u00a0': ' ',  # Non-breaking space
            '\u2019': "'",  # Curly apostrophe
            '\u201c': '"',  # Left curly quote
            '\u201d': '"',  # Right curly quote
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2026': '...',  # Ellipsis
            '\u00bb': '"',  # Right-pointing double angle quotation mark
            '\u00ab': '"'   # Left-pointing double angle quotation mark
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip()
    
    def _determine_page_type(self, url: str) -> str:
        """Determine page type based on URL"""
        url_lower = url.lower()
        if '/about' in url_lower:
            return 'about'
        elif '/service' in url_lower:
            return 'services'
        elif '/project' in url_lower:
            return 'projects'
        elif '/contact' in url_lower:
            return 'contact'
        elif '/privacy' in url_lower or '/privacy-policy' in url_lower:
            return 'privacy'
        elif '/home' in url_lower or url_lower.endswith('/'):
            return 'home'
        else:
            return 'other'
    
    async def scrape_all_company_pages(self) -> List[WebsiteContent]:
        """Extract all company pages using SerpAPI only"""
        try:
            log_function_call("scrape_all_company_pages")
            logger.info("Starting comprehensive website content extraction using SerpAPI only")
            
            scraped_content = []
            
            for url in self.target_pages:
                logger.info(f"Extracting content from: {url}")
                
                content = await self.extract_page_content_via_serpapi(url)
                
                if content:
                    scraped_content.append(content)
                    logger.info(f"Successfully extracted content from {url}: {len(content.content)} characters - Type: {content.page_type}")
                else:
                    logger.warning(f"Failed to extract content from {url}")
                
                # Respectful delay between API calls
                await asyncio.sleep(2)
            
            logger.info(f"Successfully processed {len(scraped_content)} out of {len(self.target_pages)} pages")
            
            # Verify we have substantial content
            total_content_length = sum(len(content.content) for content in scraped_content)
            logger.info(f"Total content extracted: {total_content_length} characters")
            
            return scraped_content
            
        except Exception as e:
            log_error(e, "scrape_all_company_pages")
            return []
    
    def chunk_content(self, content: WebsiteContent, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
        """Split content into optimized chunks for vector storage"""
        try:
            text = content.content
            if not text or len(text) < 50:
                logger.warning(f"Insufficient content to chunk for {content.url}")
                return []
            
            chunks = []
            
            # If content is small enough, keep as single chunk
            if len(text) <= chunk_size:
                chunks.append({
                    'text': text,
                    'metadata': {
                        'url': content.url,
                        'title': content.title,
                        'page_type': content.page_type,
                        'chunk_index': 0,
                        'total_chunks': 1,
                        'extraction_method': 'serpapi',
                        'indexed_at': datetime.now().isoformat()
                    }
                })
                return chunks
            
            # Split by sentences for better semantic chunks
            sentences = []
            # Simple sentence splitting - can be improved with NLTK if needed
            import re
            sentence_endings = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentence_endings:
                sentence = sentence.strip()
                if sentence:
                    sentences.append(sentence)
            
            if not sentences:
                # Fallback to paragraph splitting
                sentences = [p.strip() for p in text.split('\n') if p.strip()]
            
            current_chunk = ""
            chunk_index = 0
            
            for sentence in sentences:
                # Check if adding this sentence would exceed chunk size
                potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
                
                if len(potential_chunk) > chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        'text': current_chunk.strip(),
                        'metadata': {
                            'url': content.url,
                            'title': content.title,
                            'page_type': content.page_type,
                            'chunk_index': chunk_index,
                            'total_chunks': 0,  # Will be updated later
                            'extraction_method': 'serpapi',
                            'indexed_at': datetime.now().isoformat()
                        }
                    })
                    
                    # Start new chunk with overlap if specified
                    if overlap > 0 and len(current_chunk) > overlap:
                        # Take last part of current chunk as overlap
                        words = current_chunk.split()
                        overlap_words = words[-overlap//6:]  # Approximate word-based overlap
                        overlap_text = ' '.join(overlap_words)
                        current_chunk = overlap_text + " " + sentence
                    else:
                        current_chunk = sentence
                    
                    chunk_index += 1
                else:
                    current_chunk = potential_chunk
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'metadata': {
                        'url': content.url,
                        'title': content.title,
                        'page_type': content.page_type,
                        'chunk_index': chunk_index,
                        'total_chunks': 0,  # Will be updated below
                        'extraction_method': 'serpapi',
                        'indexed_at': datetime.now().isoformat()
                    }
                })
            
            # Update total chunks count
            total_chunks = len(chunks)
            for chunk in chunks:
                chunk['metadata']['total_chunks'] = total_chunks
            
            logger.info(f"Created {len(chunks)} chunks for {content.page_type} page from {content.url}")
            return chunks
            
        except Exception as e:
            log_error(e, f"chunk_content for {content.url}")
            return []

# Create global instance
serpapi_service = SerpAPIService()