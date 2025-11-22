import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

MAX_CONCURRENCY = 30  # Reduced to be safer on server
MAX_URLS = 10000  # Limit total URLs to prevent memory issues

class AsyncURLDiscovery:
    def __init__(self, seed_urls, allowed_domain, max_urls=MAX_URLS):
        self.seed_urls = seed_urls
        self.allowed_domain = allowed_domain
        self.max_urls = max_urls
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self.visited = set()
        self.found_urls = set()
        
    def normalize_url(self, base, url):
        """Normalize a URL but preserve double slashes inside path"""
        absolute = urljoin(base, url)
        
        if "//" in url and not url.startswith("http"):
            parsed = urlparse(absolute)
            return f"{parsed.scheme}://{parsed.netloc}{url.replace(' ', '%20')}"
        
        return absolute.replace(" ", "%20")
    
    async def fetch(self, session, url):
        """Fetch a single URL"""
        try:
            async with self.semaphore:
                async with session.get(url, timeout=10, ssl=False) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    
                    # Save all URLs even if not HTML
                    self.found_urls.add(url)
                    
                    if "text/html" not in content_type:
                        return None
                    
                    return await resp.text()
        except Exception as e:
            return None
    
    async def crawl_url(self, session, url):
        """Crawl a single URL and find all links"""
        if url in self.visited or len(self.found_urls) >= self.max_urls:
            return
        
        self.visited.add(url)
        print(f"  Discovering: {url}")
        
        html = await self.fetch(session, url)
        
        if not html:
            return
        
        soup = BeautifulSoup(html, "lxml")
        
        tasks = []
        
        for tag in soup.find_all("a", href=True):
            if len(self.found_urls) >= self.max_urls:
                break
                
            href = tag["href"].strip()
            
            # Skip unusable links
            if href.startswith(("mailto:", "javascript:", "#", "tel:")):
                continue
            
            new_url = self.normalize_url(url, href)
            parsed = urlparse(new_url)
            
            # Only subdomains of allowed domain
            if not parsed.netloc.endswith(self.allowed_domain):
                continue
            
            # Add to final list
            self.found_urls.add(new_url)
            
            # Crawl only HTML pages
            if new_url not in self.visited and len(self.found_urls) < self.max_urls:
                tasks.append(asyncio.ensure_future(self.crawl_url(session, new_url)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def discover(self):
        """Main discovery function"""
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                asyncio.ensure_future(self.crawl_url(session, url))
                for url in self.seed_urls
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return sorted(self.found_urls)

def discover_urls(seed_urls, domain, max_urls=MAX_URLS):
    """
    Synchronous wrapper for async URL discovery
    
    Args:
        seed_urls: List of starting URLs
        domain: Allowed domain (e.g., 'kluniversity.in')
        max_urls: Maximum URLs to discover
    
    Returns:
        List of discovered URLs
    """
    print(f"\n🔍 Phase 1: URL Discovery")
    print(f"   Starting from {len(seed_urls)} seed URL(s)")
    print(f"   Max URLs: {max_urls}")
    print(f"   Domain: {domain}\n")
    
    discovery = AsyncURLDiscovery(seed_urls, domain, max_urls)
    
    # Run async discovery
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        urls = loop.run_until_complete(discovery.discover())
    finally:
        loop.close()
    
    print(f"\n✅ Discovery complete! Found {len(urls)} URLs")
    return urls

if __name__ == "__main__":
    # Test the discovery
    seed_urls = [
        "https://www.kluniversity.in/",
    ]
    
    domain = "kluniversity.in"
    
    urls = discover_urls(seed_urls, domain, max_urls=1000)
    
    print(f"\nFirst 10 URLs:")
    for url in urls[:10]:
        print(f"  {url}")
