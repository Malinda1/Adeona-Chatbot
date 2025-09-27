# Web scraping service
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from backend.app.config.settings import settings
from backend.app.utils.logger import logger, log_error, log_function_call
from backend.app.models.chat_models import WebsiteContent

class WebScraper:
    """Web scraper for extracting content from Adeona Technologies website"""
    
    def __init__(self):
        self.base_url = settings.WEBSITE_URL
        self.pages = settings.WEBSITE_PAGES
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        # Remove special characters that might interfere with processing
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2019', "'")  # Curly apostrophe
        text = text.replace('\u201c', '"').replace('\u201d', '"')  # Curly quotes
        
        return text.strip()
    
    def extract_page_content(self, html: str, url: str) -> WebsiteContent:
        """Extract structured content from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = self.clean_text(title_tag.get_text()) if title_tag else "Adeona Technologies"
            
            # Extract main content areas
            content_selectors = [
                'main', 'article', '.content', '.main-content', 
                '#content', '.page-content', '.container'
            ]
            
            content_parts = []
            
            # Try to find main content area
            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                # Extract headings with their content
                headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in headings:
                    heading_text = self.clean_text(heading.get_text())
                    if heading_text and len(heading_text) > 2:
                        content_parts.append(f"# {heading_text}")
                        
                        # Get content after heading
                        next_sibling = heading.find_next_sibling()
                        if next_sibling:
                            sibling_text = self.clean_text(next_sibling.get_text())
                            if sibling_text and len(sibling_text) > 10:
                                content_parts.append(sibling_text)
                
                # Extract paragraphs
                paragraphs = main_content.find_all('p')
                for p in paragraphs:
                    p_text = self.clean_text(p.get_text())
                    if p_text and len(p_text) > 20:  # Filter out very short paragraphs
                        content_parts.append(p_text)
                
                # Extract lists
                lists = main_content.find_all(['ul', 'ol'])
                for list_elem in lists:
                    list_items = []
                    for li in list_elem.find_all('li'):
                        li_text = self.clean_text(li.get_text())
                        if li_text:
                            list_items.append(f"- {li_text}")
                    
                    if list_items:
                        content_parts.extend(list_items)
            
            # Combine all content
            full_content = '\n\n'.join(content_parts) if content_parts else self.clean_text(soup.get_text())
            
            # Determine page type
            page_type = self.get_page_type(url)
            
            return WebsiteContent(
                url=url,
                title=title,
                content=full_content,
                page_type=page_type
            )
            
        except Exception as e:
            log_error(e, f"extract_page_content for {url}")
            return WebsiteContent(
                url=url,
                title="Error",
                content="Failed to extract content",
                page_type="error"
            )
    
    def get_page_type(self, url: str) -> str:
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
        elif '/privacy' in url_lower:
            return 'privacy'
        elif url_lower.endswith('/') or url_lower.split('/')[-1] == '':
            return 'home'
        else:
            return 'other'
    
    async def scrape_page(self, page_path: str) -> Optional[WebsiteContent]:
        """Scrape a single page"""
        try:
            url = f"{self.base_url}{page_path}"
            log_function_call("scrape_page", {"url": url})
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    content = self.extract_page_content(html, url)
                    logger.info(f"Successfully scraped {url} - {len(content.content)} characters")
                    return content
                else:
                    logger.warning(f"Failed to scrape {url} - Status: {response.status}")
                    return None
                    
        except Exception as e:
            log_error(e, f"scrape_page for {page_path}")
            return None
    
    async def scrape_all_pages(self) -> List[WebsiteContent]:
        """Scrape all configured pages"""
        try:
            log_function_call("scrape_all_pages", {"pages_count": len(self.pages)})
            
            scraped_content = []
            
            for page_path in self.pages:
                content = await self.scrape_page(page_path)
                if content:
                    scraped_content.append(content)
                
                # Add delay between requests to be respectful
                await asyncio.sleep(1)
            
            logger.info(f"Successfully scraped {len(scraped_content)} pages")
            return scraped_content
            
        except Exception as e:
            log_error(e, "scrape_all_pages")
            return []
    
    def chunk_content(self, content: WebsiteContent, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, str]]:
        """Split content into chunks for better vector storage"""
        try:
            text = content.content
            chunks = []
            
            if len(text) <= chunk_size:
                chunks.append({
                    'text': text,
                    'metadata': {
                        'url': content.url,
                        'title': content.title,
                        'page_type': content.page_type,
                        'chunk_index': 0
                    }
                })
                return chunks
            
            start = 0
            chunk_index = 0
            
            while start < len(text):
                end = start + chunk_size
                
                # Try to break at a sentence or paragraph boundary
                if end < len(text):
                    # Look for sentence ending
                    last_period = text.rfind('.', start, end)
                    last_newline = text.rfind('\n', start, end)
                    
                    break_point = max(last_period, last_newline)
                    if break_point > start + chunk_size // 2:  # Only if we found a good break point
                        end = break_point + 1
                
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'metadata': {
                            'url': content.url,
                            'title': content.title,
                            'page_type': content.page_type,
                            'chunk_index': chunk_index
                        }
                    })
                    chunk_index += 1
                
                start = end - overlap if end < len(text) else end
            
            logger.info(f"Split content into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            log_error(e, "chunk_content")
            return []

# Create global instance
web_scraper = WebScraper()