import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import time
from langchain_core.documents import Document
from datetime import datetime
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RecursiveCrawler:
    def __init__(self, base_url, max_depth=4, max_pages=5000):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited = set()
        self.documents = []
        self.error_count = 0
        self.max_errors = 100
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"crawl_log_{timestamp}.txt"
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Crawl Log - {datetime.now()}\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Max Depth: {max_depth}\n")
            f.write(f"Max Pages: {max_pages}\n")
            f.write("="*60 + "\n\n")

    def log_to_file(self, message):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        except Exception as e:
            print(f"Error writing to log: {e}")

    def is_valid_url(self, url):
        try:
            parsed = urlparse(url)
            
            if not (parsed.netloc == self.domain or parsed.netloc.endswith('.' + self.domain)):
                return False
            
            skip_patterns = [
                r'/login', r'/logout', r'/signin', r'/signup',
                r'/admin', r'/api/', r'/wp-admin',
                r'/print/', r'/download/',
                r'\.pdf$', r'\.jpg$', r'\.jpeg$', r'\.png$', 
                r'\.gif$', r'\.svg$', r'\.webp$', r'\.ico$',
                r'\.css$', r'\.js$', r'\.xml$', r'\.json$',
                r'\.zip$', r'\.tar$', r'\.gz$',
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

    def crawl(self, url, depth=0):
        if (depth > self.max_depth or url in self.visited or 
            len(self.documents) >= self.max_pages or self.error_count >= self.max_errors):
            return

        url = self.normalize_url(url)
        
        if not self.is_valid_url(url):
            return

        print(f"[Depth {depth}] Crawling: {url}")
        self.log_to_file(f"[CRAWLING] Depth {depth}: {url}")
        self.visited.add(url)

        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                self.log_to_file(f"[ERROR] Failed to fetch {url}: Status {response.status_code}")
                self.error_count += 1
                return

            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'text/plain', 'application/xhtml']):
                self.log_to_file(f"[SKIPPED] Non-HTML: {url}")
                return

            soup = BeautifulSoup(response.content, 'html.parser')
            text = self.extract_text_from_soup(soup)
            
            if len(text) > 1_000_000 or len(text) < 100:
                self.log_to_file(f"[SKIPPED] Invalid size: {url} ({len(text)} chars)")
                return
            
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ""
            
            self.documents.append(Document(
                page_content=text,
                metadata={
                    "source": url,
                    "title": title,
                    "description": description,
                    "depth": depth,
                    "crawled_at": datetime.utcnow().isoformat()
                }
            ))
            
            print(f"✓ Scraped: {url} ({len(text)} chars, {len(self.documents)}/{self.max_pages})")
            self.log_to_file(f"[SUCCESS] {url}")

            time.sleep(0.5)

            if len(self.documents) < self.max_pages and depth < self.max_depth:
                links = soup.find_all('a', href=True)
                for link in links:
                    if len(self.documents) >= self.max_pages:
                        break
                    full_url = self.normalize_url(urljoin(url, link['href']))
                    if full_url not in self.visited and self.is_valid_url(full_url):
                        self.crawl(full_url, depth + 1)
                    
        except Exception as e:
            self.log_to_file(f"[ERROR] {url}: {type(e).__name__}")
            self.error_count += 1

    def start(self):
        print(f"\n🚀 Starting crawl of {self.base_url}")
        print(f"📊 Limits: Max depth={self.max_depth}, Max pages={self.max_pages}")
        
        self.crawl(self.base_url)
        
        self.log_to_file(f"\n{'='*60}")
        self.log_to_file(f"Crawl completed at {datetime.now()}")
        self.log_to_file(f"Total pages: {len(self.documents)}")
        self.log_to_file(f"Total errors: {self.error_count}")
        
        print(f"\n✅ Crawl complete!")
        print(f"📄 Pages collected: {len(self.documents)}")
        print(f"⚠️  Errors: {self.error_count}")
        print(f"📝 Log: {self.log_file}")
        
        return self.documents