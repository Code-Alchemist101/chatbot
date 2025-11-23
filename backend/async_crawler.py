import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from langchain_core.documents import Document
from datetime import datetime
import re
from logger import setup_logger
from config import MAX_CONCURRENCY

# Setup logging
logger = setup_logger(__name__)

class AsyncRecursiveCrawler:
    def __init__(self, base_url, max_depth=4, max_pages=100000, concurrency=20):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.visited = set()
        self.documents = []
        self.error_count = 0
        self.max_errors = 100
        self.semaphore = asyncio.Semaphore(concurrency)
        self.lock = asyncio.Lock()
        
        # Create log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"crawl_log_{timestamp}.txt"
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Async Crawl Log - {datetime.now()}\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Max Depth: {max_depth}\n")
            f.write(f"Max Pages: {max_pages}\n")
            f.write(f"Concurrency: {concurrency}\n")
            f.write("="*60 + "\n\n")

    def log_to_file(self, message):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        except Exception as e:
            logger.error(f"Error writing to log: {e}")

    def is_valid_url(self, url):
        try:
            parsed = urlparse(url)
            
            if not (parsed.netloc == self.domain or parsed.netloc.endswith('.' + self.domain)):
                return False
            
            skip_patterns = [
                # Authentication & Admin
                r'/login', r'/logout', r'/signin', r'/signup',
                r'/admin', r'/api/', r'/wp-admin',
                r'/print/', r'/download/',
                # Images
                r'\.pdf$', r'\.jpg$', r'\.jpeg$', r'\.png$', 
                r'\.gif$', r'\.svg$', r'\.webp$', r'\.ico$', r'\.bmp$',
                # Videos
                r'\.mp4$', r'\.avi$', r'\.mov$', r'\.wmv$', r'\.flv$', r'\.webm$', r'\.mkv$',
                # Audio
                r'\.mp3$', r'\.wav$', r'\.ogg$', r'\.m4a$', r'\.flac$', r'\.aac$',
                # Office Documents
                r'\.doc$', r'\.docx$', r'\.xls$', r'\.xlsx$', r'\.ppt$', r'\.pptx$',
                # Code & Data
                r'\.css$', r'\.js$', r'\.xml$', r'\.json$',
                # Archives
                r'\.zip$', r'\.tar$', r'\.gz$', r'\.rar$', r'\.7z$',
                # Query Parameters
                r'\?share=', r'\?print=', r'\?replytocom='
            ]
            
            for pattern in skip_patterns:
                if re.search(pattern, url.lower()):
                    return False
            
            return True
        except Exception:
            return False

    def normalize_url(self, url):
        url, _ = urldefrag(url)
        return url.rstrip('/')

    def extract_text_from_soup(self, soup):
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)

    async def fetch_and_parse(self, session, url, depth):
        """Fetch a single URL and extract content"""
        async with self.lock:
            if (url in self.visited or len(self.documents) >= self.max_pages or 
                self.error_count >= self.max_errors):
                return None
            self.visited.add(url)
        
        try:
            async with self.semaphore:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as response:
                    if response.status != 200:
                        self.log_to_file(f"[ERROR] Failed to fetch {url}: Status {response.status}")
                        async with self.lock:
                            self.error_count += 1
                        return None

                    content_type = response.headers.get('Content-Type', '').lower()
                    if not any(t in content_type for t in ['text/html', 'text/plain', 'application/xhtml']):
                        self.log_to_file(f"[SKIPPED] Non-HTML: {url}")
                        return None

                    html = await response.text()
                    
        except Exception as e:
            self.log_to_file(f"[ERROR] {url}: {type(e).__name__}")
            async with self.lock:
                self.error_count += 1
            return None

        # Parse HTML (CPU-bound, but fast enough)
        try:
            soup = BeautifulSoup(html, 'lxml')
            text = self.extract_text_from_soup(soup)
            
            if len(text) > 1_000_000 or len(text) < 100:
                self.log_to_file(f"[SKIPPED] Invalid size: {url} ({len(text)} chars)")
                return None
            
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ""
            
            doc = Document(
                page_content=text,
                metadata={
                    "source": url,
                    "title": title,
                    "description": description,
                    "depth": depth,
                    "crawled_at": datetime.utcnow().isoformat()
                }
            )
            
            async with self.lock:
                self.documents.append(doc)
                doc_count = len(self.documents)
            
            logger.info(f"Scraped: {url} ({len(text)} chars, {doc_count}/{self.max_pages})")
            self.log_to_file(f"[SUCCESS] {url}")
            
            return doc
            
        except Exception as e:
            self.log_to_file(f"[ERROR] Parsing {url}: {type(e).__name__}")
            async with self.lock:
                self.error_count += 1
            return None

    async def crawl_urls(self, urls):
        """Crawl a list of URLs concurrently"""
        connector = aiohttp.TCPConnector(
            limit=self.concurrency,
            limit_per_host=10,
            force_close=True
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            tasks = []
            for url in urls:
                if len(self.documents) >= self.max_pages:
                    break
                
                url = self.normalize_url(url)
                if not self.is_valid_url(url):
                    continue
                
                if url not in self.visited:
                    tasks.append(self.fetch_and_parse(session, url, depth=0))
            
            # Process all URLs concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

    async def start_async(self, urls):
        """Start async crawling"""
        logger.info(f"Starting async crawl with {len(urls)} URLs")
        logger.info(f"Limits: Max pages={self.max_pages}, Concurrency={self.concurrency}")
        
        await self.crawl_urls(urls)
        
        self.log_to_file(f"\n{'='*60}")
        self.log_to_file(f"Crawl completed at {datetime.now()}")
        self.log_to_file(f"Total pages: {len(self.documents)}")
        self.log_to_file(f"Total errors: {self.error_count}")
        
        logger.info(f"Crawl complete!")
        logger.info(f"Pages collected: {len(self.documents)}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Log: {self.log_file}")
        
        return self.documents

def crawl_urls_async(urls, base_url, max_pages=100000, concurrency=20):
    """Synchronous wrapper for async crawling"""
    crawler = AsyncRecursiveCrawler(base_url, max_depth=1, max_pages=max_pages, concurrency=concurrency)
    
    # Run async crawl
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Silence Windows socket errors
    def exception_handler(loop, context):
        msg = context.get("exception", context.get("message"))
        if "WinError 10022" in str(msg) or "WinError 10038" in str(msg):
            return
        loop.default_exception_handler(context)
    
    loop.set_exception_handler(exception_handler)
    
    try:
        documents = loop.run_until_complete(crawler.start_async(urls))
        loop.run_until_complete(asyncio.sleep(0.25))
    finally:
        loop.close()
    
    return documents, crawler.log_file
