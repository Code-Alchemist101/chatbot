import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from langchain_core.documents import Document
from datetime import datetime

class RecursiveCrawler:
    def __init__(self, base_url, max_depth=2):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.visited = set()
        self.documents = []
        
        # Create log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"crawl_log_{timestamp}.txt"
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Crawl Log - Started at {datetime.now()}\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Max Depth: {max_depth}\n")
            f.write("="*60 + "\n\n")

    def log_to_file(self, message):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.domain

    def crawl(self, url, depth=0):
        if depth > self.max_depth or url in self.visited:
            return

        # Skip binary files (PDFs, images, etc.)
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico']):
            skip_msg = f"⏭️  Skipping binary file: {url}"
            print(skip_msg)
            self.log_to_file(f"[SKIPPED] {skip_msg}")
            self.visited.add(url)
            return

        print(f"Crawling: {url}")
        self.log_to_file(f"[CRAWLING] Depth {depth}: {url}")
        self.visited.add(url)

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                error_msg = f"Failed to fetch {url}: Status {response.status_code}"
                print(error_msg)
                self.log_to_file(f"[ERROR] {error_msg}")
                return

            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(t in content_type for t in ['text/html', 'text/plain', 'application/xhtml']):
                skip_msg = f"⏭️  Skipping non-HTML content: {url} ({content_type})"
                print(skip_msg)
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            # Skip if text is too large (> 1MB) or too small (< 100 chars)
            if len(text) > 1_000_000:
                skip_msg = f"⏭️  Skipping oversized content: {url} ({len(text)} chars)"
                print(skip_msg)
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return
            
            if len(text) < 100:
                skip_msg = f"⏭️  Skipping minimal content: {url} ({len(text)} chars)"
                print(skip_msg)
                self.log_to_file(f"[SKIPPED] {skip_msg}")
                return
            
            # Create a Document object
            if text:
                self.documents.append(Document(
                    page_content=text,
                    metadata={"source": url, "title": soup.title.string if soup.title else ""}
                ))
                success_msg = f"✓ Scraped: {url} ({len(text)} chars)"
                print(success_msg)
                self.log_to_file(f"[SUCCESS] {success_msg}")

            # Add delay to avoid overwhelming the server
            time.sleep(0.5)

            # Find links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                
                # Remove fragments
                full_url = full_url.split('#')[0]

                if self.is_valid_url(full_url) and full_url not in self.visited:
                    self.crawl(full_url, depth + 1)
                    
        except Exception as e:
            error_msg = f"✗ Error crawling {url}: {e}"
            print(error_msg)
            self.log_to_file(f"[ERROR] {error_msg}")

    def start(self):
        self.crawl(self.base_url)
        self.log_to_file(f"\n{'='*60}")
        self.log_to_file(f"Crawl completed at {datetime.now()}")
        self.log_to_file(f"Total pages crawled: {len(self.documents)}")
        self.log_to_file(f"Log file: {self.log_file}")
        print(f"\n📝 Crawl log saved to: {self.log_file}")
        return self.documents

if __name__ == "__main__":
    # Test
    crawler = RecursiveCrawler("https://www.kluniversity.in", max_depth=1)
    docs = crawler.start()
    print(f"Found {len(docs)} documents.")
