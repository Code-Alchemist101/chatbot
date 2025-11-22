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
    def __init__(self, base_url, max_depth=2, max_pages=2000):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.visited = set()
        self.documents = []
        self.error_count = 0
        self.max_errors = 50
        
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
        
        # Set proper headers
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
            
            # Check if same domain or subdomain
            if not (parsed.netloc == self.domain or 
                    parsed.netloc.endswith('.' + self.domain)):
                return False
            
            # Skip common non-content URLs
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
        """Remove fragments and normalize URL"""
        url, _ = urldefrag(url)
        return url.rstrip('/')

    def extract_text_from_soup(self, soup):
        """Extract clean text from BeautifulSoup object"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 
                            'header', 'aside', 'iframe', 'noscript']):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        
        return text

    def crawl(self, url, depth=0):
        # Check limits
        if (depth > self.max_depth or 
            url in self.visited or 
            len(self.documents) >= self.max_pages or
            self.error_count >= self.max_errors):
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
                error_msg = f"Failed to fetch {url}: Status {response.status_code}"
                print(f"⚠️  {error_msg}")
                self.log_to_file(f"[ERROR] {error_msg}")
                self.error_count += 1
                return

            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'text/plain', 
                                                     'application/xhtml']):
                skip_msg = f"Skipping non-HTML: {url} ({content_type})"
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            text = self.extract_text_from_soup(soup)
            
            # Validate content size
            if len(text) > 1_000_000:
                skip_msg = f"Skipping oversized content: {url} ({len(text)} chars)"
                print(f"⏭️  {skip_msg}")
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return
            
            if len(text) < 100:
                skip_msg = f"Skipping minimal content: {url} ({len(text)} chars)"
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return
            
            # Get page title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            
            # Get meta description
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()
            
            # Create Document
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
            
            success_msg = f"✓ Scraped: {url} ({len(text)} chars, {len(self.documents)}/{self.max_pages})"
            print(success_msg)
            self.log_to_file(f"[SUCCESS] {success_msg}")

            # Rate limiting
            time.sleep(0.5)

            # Find and crawl links (only if we haven't hit the page limit)
            if len(self.documents) < self.max_pages and depth < self.max_depth:
                links = soup.find_all('a', href=True)
                print(f"  Found {len(links)} links to process")
                
                for link in links:
                    if len(self.documents) >= self.max_pages:
                        break
                        
                    href = link['href']
                    full_url = urljoin(url, href)
                    full_url = self.normalize_url(full_url)
                    
                    if full_url not in self.visited and self.is_valid_url(full_url):
                        self.crawl(full_url, depth + 1)
                    
        except requests.exceptions.Timeout:
            error_msg = f"Timeout fetching {url}"
            print(f"⏱️  {error_msg}")
            self.log_to_file(f"[ERROR] {error_msg}")
            self.error_count += 1
            
        except requests.exceptions.TooManyRedirects:
            error_msg = f"Too many redirects: {url}"
            print(f"🔄 {error_msg}")
            self.log_to_file(f"[ERROR] {error_msg}")
            self.error_count += 1
            
        except Exception as e:
            error_msg = f"Error crawling {url}: {type(e).__name__}: {str(e)}"
            print(f"✗ {error_msg}")
            self.log_to_file(f"[ERROR] {error_msg}")
            self.error_count += 1

    def start(self):
        print(f"\n🚀 Starting crawl of {self.base_url}")
        print(f"📊 Limits: Max depth={self.max_depth}, Max pages={self.max_pages}")
        
        self.crawl(self.base_url)
        
        self.log_to_file(f"\n{'='*60}")
        self.log_to_file(f"Crawl completed at {datetime.now()}")
        self.log_to_file(f"Total pages crawled: {len(self.documents)}")
        self.log_to_file(f"Total errors: {self.error_count}")
        self.log_to_file(f"Log file: {self.log_file}")
        
        print(f"\n✅ Crawl complete!")
        print(f"📄 Pages collected: {len(self.documents)}")
        print(f"⚠️  Errors encountered: {self.error_count}")
        print(f"📝 Log saved to: {self.log_file}")
        
        return self.documents

if __name__ == "__main__":
    crawler = RecursiveCrawler("https://www.kluniversity.in", max_depth=2, max_pages=2000)
    docs = crawler.start()
    print(f"\nFinal count: {len(docs)} documents.")