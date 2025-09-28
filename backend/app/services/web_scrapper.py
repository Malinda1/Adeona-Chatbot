import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
import time
import os
import re
import logging
from datetime import datetime
from collections import deque
import json
from typing import Set, Dict, List, Optional
import hashlib
from dataclasses import dataclass
import csv
import ssl
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class ScrapedPage:
    """Data class to store scraped page information"""
    url: str
    title: str
    content: str
    meta_description: str
    headers: List[str]
    links: List[str]
    images: List[str]
    timestamp: str
    status_code: int
    word_count: int
    raw_html: str

class ProfessionalWebScraper:
    """
    Enhanced industrial-level web scraper with:
    - JavaScript support via Selenium
    - Better content extraction
    - SSL handling
    - Multiple fallback methods
    """
    
    def __init__(self, base_url: str, delay: float = 2.0, max_pages: int = 1000, use_selenium: bool = True):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.delay = delay
        self.max_pages = max_pages
        self.use_selenium = use_selenium
        
        # Data storage
        self.visited_urls: Set[str] = set()
        self.scraped_pages: List[ScrapedPage] = []
        self.failed_urls: Dict[str, str] = {}
        
        # Queue for BFS crawling
        self.url_queue = deque([base_url])
        
        # Setup requests session with SSL handling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Disable SSL verification for problematic sites
        self.session.verify = False
        
        # Setup logging first
        self.setup_logging()
        
        # Setup Selenium if requested
        self.driver = None
        if self.use_selenium:
            self.setup_selenium()
        
        # Create output directory
        self.output_dir = f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def setup_selenium(self):
        """Setup Selenium WebDriver for JavaScript support"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--ignore-certificate-errors-spki-list')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.logger.info("✅ Selenium WebDriver initialized successfully")
        except ImportError:
            self.logger.warning("⚠️ Selenium not installed. Install with: pip install selenium")
            self.driver = None
            self.use_selenium = False
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Selenium: {e}. Falling back to requests only.")
            self.logger.info("💡 Make sure ChromeDriver is installed: brew install chromedriver")
            self.driver = None
            self.use_selenium = False
        
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the same domain"""
        try:
            parsed = urlparse(url)
            
            # Skip non-http protocols
            if parsed.scheme not in ['http', 'https', '']:
                return False
                
            # Same domain check (allow relative URLs)
            if parsed.netloc and parsed.netloc != self.domain:
                return False
                
            # Skip non-HTML files
            if parsed.path.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.exe', '.jpg', '.png', '.gif', '.css', '.js')):
                return False
                
            return True
        except:
            return False
            
    def normalize_url(self, url: str) -> str:
        """Normalize URL to avoid duplicates"""
        try:
            # Handle relative URLs
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)
                
            parsed = urlparse(url)
            # Remove fragment and normalize
            normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                   parsed.params, parsed.query, ''))
            return normalized.rstrip('/')
        except:
            return url
            
    def extract_content_advanced(self, soup: BeautifulSoup, html_content: str) -> Dict[str, any]:
        """Advanced content extraction with multiple strategies"""
        content_data = {}
        
        # Title extraction with fallbacks
        title_tag = soup.find('title')
        if title_tag:
            content_data['title'] = title_tag.text.strip()
        else:
            # Try h1 as title fallback
            h1_tag = soup.find('h1')
            content_data['title'] = h1_tag.text.strip() if h1_tag else 'No title found'
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        content_data['meta_description'] = meta_desc.get('content', '').strip() if meta_desc else ''
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
            
        # Multiple content extraction strategies
        content_parts = []
        
        # Strategy 1: Look for main content containers
        main_selectors = [
            'main', 'article', '.main-content', '#main-content', '.content', '#content',
            '.post-content', '.entry-content', '.page-content', '.article-content',
            '.main', '#main', '.container', '.wrapper', 'section'
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Only consider substantial content
                    content_parts.append(text)
                    break
            if content_parts:
                break
                
        # Strategy 2: Extract from body if no main content found
        if not content_parts and soup.body:
            content_parts.append(soup.body.get_text(separator=' ', strip=True))
            
        # Strategy 3: Extract all text as fallback
        if not content_parts:
            content_parts.append(soup.get_text(separator=' ', strip=True))
            
        # Clean and combine content
        content_text = ' '.join(content_parts)
        content_text = re.sub(r'\s+', ' ', content_text).strip()
        content_data['content'] = content_text
        
        # Headers extraction
        headers = []
        for i in range(1, 7):
            header_tags = soup.find_all(f'h{i}')
            for header in header_tags:
                header_text = header.get_text(strip=True)
                if header_text and len(header_text) < 200:  # Reasonable header length
                    headers.append(header_text)
        content_data['headers'] = headers
        
        # Links extraction
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if href and self.is_valid_url(href):
                absolute_url = self.normalize_url(href)
                if absolute_url:
                    links.add(absolute_url)
        content_data['links'] = list(links)
        
        # Images extraction
        images = []
        for img in soup.find_all('img', src=True):
            img_src = img['src'].strip()
            if img_src:
                img_url = urljoin(self.base_url, img_src)
                images.append(img_url)
        content_data['images'] = list(set(images))
        
        return content_data
        
    def scrape_with_requests(self, url: str) -> Optional[tuple]:
        """Scrape using requests library"""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            return response.text, response.status_code
        except Exception as e:
            self.logger.error(f"Requests scraping failed for {url}: {e}")
            return None, None
            
    def scrape_with_selenium(self, url: str) -> Optional[tuple]:
        """Scrape using Selenium for JavaScript support"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            html_content = self.driver.page_source
            return html_content, 200
        except Exception as e:
            self.logger.error(f"❌ Selenium scraping failed for {url}: {e}")
            return None, None
            
    def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """Scrape a single page with multiple fallback methods"""
        html_content = None
        status_code = None
        
        # Try Selenium first if available
        if self.use_selenium and self.driver:
            html_content, status_code = self.scrape_with_selenium(url)
            
        # Fallback to requests if Selenium fails
        if not html_content:
            html_content, status_code = self.scrape_with_requests(url)
            
        if not html_content:
            self.failed_urls[url] = "Failed to fetch content with both methods"
            return None
            
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content using advanced methods
            content_data = self.extract_content_advanced(soup, html_content)
            
            # Create ScrapedPage object
            scraped_page = ScrapedPage(
                url=url,
                title=content_data['title'],
                content=content_data['content'],
                meta_description=content_data['meta_description'],
                headers=content_data['headers'],
                links=content_data['links'],
                images=content_data['images'],
                timestamp=datetime.now().isoformat(),
                status_code=status_code or 200,
                word_count=len(content_data['content'].split()) if content_data['content'] else 0,
                raw_html=html_content[:5000]  # Store first 5000 chars for debugging
            )
            
            # Add discovered links to queue
            for link in content_data['links']:
                normalized_link = self.normalize_url(link)
                if (normalized_link not in self.visited_urls and 
                    normalized_link not in [self.normalize_url(u) for u in self.url_queue]):
                    self.url_queue.append(normalized_link)
                    
            self.logger.info(f"✅ Successfully scraped: {url} ({scraped_page.word_count} words)")
            return scraped_page
            
        except Exception as e:
            self.logger.error(f"❌ Error processing {url}: {e}")
            self.failed_urls[url] = str(e)
            return None
            
    def save_individual_page(self, page: ScrapedPage):
        """Save individual page to text file"""
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', page.title)[:50]
        url_hash = hashlib.md5(page.url.encode()).hexdigest()[:8]
        filename = f"{safe_title}_{url_hash}.txt"
        filepath = os.path.join(self.output_dir, 'individual_pages', filename)
        
        # Create directory
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"URL: {page.url}\n")
            f.write(f"Title: {page.title}\n")
            f.write(f"Scraped: {page.timestamp}\n")
            f.write(f"Word Count: {page.word_count}\n")
            f.write(f"Status Code: {page.status_code}\n")
            f.write("="*80 + "\n\n")
            
            if page.meta_description:
                f.write(f"Meta Description: {page.meta_description}\n\n")
                
            if page.headers:
                f.write("Headers Found:\n")
                for header in page.headers:
                    f.write(f"- {header}\n")
                f.write("\n")
                
            f.write("MAIN CONTENT:\n")
            f.write("-"*40 + "\n")
            f.write(page.content if page.content else "No content extracted")
            f.write("\n\n")
            
            # Debug info
            f.write("DEBUG INFO:\n")
            f.write("-"*20 + "\n")
            f.write(f"Raw HTML (first 1000 chars):\n{page.raw_html[:1000]}...")
            
    def save_consolidated_data(self):
        """Save all data in consolidated formats"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Single consolidated text file with ALL content
        consolidated_file = os.path.join(self.output_dir, f'COMPLETE_WEBSITE_CONTENT_{timestamp}.txt')
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            f.write(f"🌐 COMPLETE WEBSITE SCRAPE: {self.base_url}\n")
            f.write(f"📅 Scrape Date: {datetime.now()}\n")
            f.write(f"📊 Total Pages: {len(self.scraped_pages)}\n")
            f.write(f"📝 Total Words: {sum(page.word_count for page in self.scraped_pages):,}\n")
            f.write(f"❌ Failed URLs: {len(self.failed_urls)}\n")
            f.write("="*100 + "\n\n")
            
            for i, page in enumerate(self.scraped_pages, 1):
                f.write(f"\n{'='*15} PAGE {i}/{len(self.scraped_pages)}: {page.title} {'='*15}\n")
                f.write(f"🔗 URL: {page.url}\n")
                f.write(f"📊 Words: {page.word_count:,}\n")
                f.write(f"⏰ Scraped: {page.timestamp}\n")
                f.write("-"*80 + "\n")
                
                if page.headers:
                    f.write("📋 HEADERS:\n")
                    for header in page.headers:
                        f.write(f"  • {header}\n")
                    f.write("\n")
                
                f.write("📄 CONTENT:\n")
                f.write(page.content if page.content else "⚠️ No content extracted")
                f.write("\n" + "="*100 + "\n")
                
        # 2. Content-only file (clean text)
        content_only_file = os.path.join(self.output_dir, f'CLEAN_TEXT_ONLY_{timestamp}.txt')
        with open(content_only_file, 'w', encoding='utf-8') as f:
            f.write(f"Clean Text Content from: {self.base_url}\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*80 + "\n\n")
            
            for page in self.scraped_pages:
                if page.content and page.word_count > 0:
                    f.write(f"\n--- {page.title} ---\n")
                    f.write(page.content)
                    f.write("\n\n")
                    
        # 3. Detailed JSON export
        json_file = os.path.join(self.output_dir, f'complete_scrape_data_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            data = {
                'scrape_metadata': {
                    'base_url': self.base_url,
                    'scrape_date': datetime.now().isoformat(),
                    'total_pages_scraped': len(self.scraped_pages),
                    'total_words_extracted': sum(page.word_count for page in self.scraped_pages),
                    'failed_urls_count': len(self.failed_urls),
                    'scraping_method': 'Selenium + Requests' if self.use_selenium else 'Requests only'
                },
                'scraped_pages': [
                    {
                        'url': page.url,
                        'title': page.title,
                        'content': page.content,
                        'meta_description': page.meta_description,
                        'headers': page.headers,
                        'internal_links': page.links,
                        'images': page.images,
                        'word_count': page.word_count,
                        'scrape_timestamp': page.timestamp,
                        'status_code': page.status_code
                    } for page in self.scraped_pages
                ],
                'failed_urls': self.failed_urls
            }
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        # 4. Summary report
        summary_file = os.path.join(self.output_dir, f'SCRAPING_REPORT_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("🎯 WEB SCRAPING SUMMARY REPORT\n")
            f.write("="*50 + "\n")
            f.write(f"Target Website: {self.base_url}\n")
            f.write(f"Scrape Completed: {datetime.now()}\n")
            f.write(f"Method Used: {'Selenium + Requests' if self.use_selenium else 'Requests only'}\n")
            f.write("\n📊 STATISTICS:\n")
            f.write(f"  • Total pages scraped: {len(self.scraped_pages)}\n")
            f.write(f"  • Total words extracted: {sum(page.word_count for page in self.scraped_pages):,}\n")
            f.write(f"  • Average words per page: {sum(page.word_count for page in self.scraped_pages) // len(self.scraped_pages) if self.scraped_pages else 0:,}\n")
            f.write(f"  • Failed URLs: {len(self.failed_urls)}\n")
            f.write(f"  • Success rate: {len(self.scraped_pages)/(len(self.scraped_pages)+len(self.failed_urls))*100:.1f}%\n")
            
            f.write("\n📄 PAGES SCRAPED:\n")
            for i, page in enumerate(self.scraped_pages, 1):
                f.write(f"  {i}. {page.title} ({page.word_count:,} words) - {page.url}\n")
                
            if self.failed_urls:
                f.write(f"\n❌ FAILED URLS ({len(self.failed_urls)}):\n")
                for url, error in self.failed_urls.items():
                    f.write(f"  • {url} - {error}\n")
                    
    def run(self):
        """Main scraping execution"""
        self.logger.info(f"🚀 Starting comprehensive scrape of {self.base_url}")
        self.logger.info(f"🔧 Using method: {'Selenium + Requests' if self.use_selenium else 'Requests only'}")
        start_time = time.time()
        
        try:
            while self.url_queue and len(self.scraped_pages) < self.max_pages:
                url = self.url_queue.popleft()
                normalized_url = self.normalize_url(url)
                
                if normalized_url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(normalized_url)
                self.logger.info(f"🔍 Scraping: {url}")
                
                # Scrape page
                scraped_page = self.scrape_page(url)
                if scraped_page:
                    self.scraped_pages.append(scraped_page)
                    # Save individual page
                    self.save_individual_page(scraped_page)
                    
                # Rate limiting
                time.sleep(self.delay)
                
                # Progress update
                if len(self.scraped_pages) % 5 == 0:
                    total_words = sum(page.word_count for page in self.scraped_pages)
                    self.logger.info(f"📊 Progress: {len(self.scraped_pages)} pages scraped, {total_words:,} words, {len(self.url_queue)} URLs in queue")
                    
        finally:
            # Clean up Selenium
            if self.driver:
                self.driver.quit()
                
        # Save all consolidated data
        self.save_consolidated_data()
        
        # Final statistics
        end_time = time.time()
        duration = end_time - start_time
        total_words = sum(page.word_count for page in self.scraped_pages)
        
        self.logger.info("="*80)
        self.logger.info("🎉 SCRAPING COMPLETED SUCCESSFULLY!")
        self.logger.info(f"📊 Total pages scraped: {len(self.scraped_pages)}")
        self.logger.info(f"📝 Total words extracted: {total_words:,}")
        self.logger.info(f"❌ Failed URLs: {len(self.failed_urls)}")
        self.logger.info(f"⏱️ Time taken: {duration:.2f} seconds")
        self.logger.info(f"📁 Output directory: {self.output_dir}")
        self.logger.info(f"💯 Success rate: {len(self.scraped_pages)/(len(self.scraped_pages)+len(self.failed_urls))*100:.1f}%")
        self.logger.info("="*80)
        
        return self.output_dir

def main():
    """Main execution function"""
    # Configuration
    BASE_URL = "https://adeonatech.net/"
    DELAY = 2.0  # seconds between requests
    MAX_PAGES = 100  # maximum pages to scrape
    
    # Try Selenium first, fallback to requests-only if it fails
    USE_SELENIUM = True
    
    print("🚀 Starting Web Scraper")
    print(f"🎯 Target: {BASE_URL}")
    
    try:
        # Initialize and run scraper
        scraper = ProfessionalWebScraper(
            base_url=BASE_URL,
            delay=DELAY,
            max_pages=MAX_PAGES,
            use_selenium=USE_SELENIUM
        )
        
        output_directory = scraper.run()
        
        print(f"\n🎉 Scraping completed successfully!")
        print(f"📁 All files saved in: {output_directory}")
        print(f"📋 Check the files:")
        print(f"   • COMPLETE_WEBSITE_CONTENT_*.txt - All content in one file")
        print(f"   • CLEAN_TEXT_ONLY_*.txt - Just the text content")
        print(f"   • complete_scrape_data_*.json - Structured data")
        print(f"   • SCRAPING_REPORT_*.txt - Summary report")
        
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print(f"💡 If you don't have ChromeDriver, the scraper will automatically fall back to requests-only mode")
        logging.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()