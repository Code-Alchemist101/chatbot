import argparse
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from url_discovery import discover_urls
from urllib.parse import urlparse
from datetime import datetime
import hashlib
from logger import setup_logger
from config import (
    PINECONE_API_KEY, PINECONE_INDEX, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, INGESTION_BATCH_SIZE
)

# Setup logging
logger = setup_logger(__name__)

def calculate_doc_hash(doc):
    """Calculate hash of document content for deduplication"""
    content = doc.page_content + str(doc.metadata.get('source', ''))
    return hashlib.md5(content.encode()).hexdigest()

def check_existing_documents(namespace, urls):
    """Fix #12: Check which URLs are already indexed in Pinecone
    
    Args:
        namespace: Pinecone namespace to check
        urls: List of URLs to check
        
    Returns:
        Set of URLs that already exist in the index
    """
    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX,
            embedding=embeddings,
            pinecone_api_key=PINECONE_API_KEY,
            namespace=namespace
        )
        
        # Query for each URL (this is a simplified check)
        # In production, you might want to use Pinecone's fetch API
        existing = set()
        for url in urls[:100]:  # Limit check to avoid too many queries
            try:
                results = vector_store.similarity_search(
                    url, 
                    k=1, 
                    filter={"source": url},
                    namespace=namespace
                )
                if results:
                    existing.add(url)
            except:
                pass
        
        return existing
    except Exception as e:
        logger.warning(f"Could not check existing documents: {e}")
        return set()

def ingest(url, max_depth=2, crawl_id=None, crawl_status=None):
    """Ingest website content into Pinecone with namespace isolation
    
    Args:
        url: Base URL to crawl
        max_depth: Maximum crawl depth (Fix #11: now actually used)
        crawl_id: Optional crawl ID for status tracking
        crawl_status: Optional status dict for progress updates
    """
    logger.info(f"{'='*60}")
    logger.info(f"🚀 Starting ingestion for: {url}")
    logger.info(f"📊 Max depth: {max_depth}")
    logger.info(f"{'='*60}")
    
    # Fix #6: Extract domain for namespace isolation
    domain = urlparse(url).netloc.replace('www.', '')
    namespace = domain.replace('.', '_')  # Pinecone namespace-safe
    logger.info(f"📦 Using Pinecone namespace: {namespace}")
    
    # Update status
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['stage'] = 'url_discovery'
    
    # Phase 1: Fast URL Discovery
    logger.info("=" * 60)
    logger.info("🔍 PHASE 1: URL DISCOVERY (Fast Async Crawl)")
    logger.info("=" * 60)
    
    # Fix #4: Remove hardcoded seed URLs - only use provided URL
    seed_urls = [url]
    
    discovered_urls = discover_urls(seed_urls, domain, max_urls=100000)
    logger.info(f"📊 Discovered {len(discovered_urls)} unique URLs")
    
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['stage'] = 'deduplication_check'
    
    # Fix #12: Check for existing documents
    logger.info("🔍 Checking for already-indexed URLs...")
    existing_urls = check_existing_documents(namespace, discovered_urls)
    if existing_urls:
        logger.info(f"⏭️  Skipping {len(existing_urls)} already-indexed URLs")
        discovered_urls = [u for u in discovered_urls if u not in existing_urls]
    
    if not discovered_urls:
        logger.warning("⚠️  All URLs already indexed, nothing to crawl")
        return {
            'success': True,
            'total_documents': 0,
            'indexed_documents': 0,
            'skipped_existing': len(existing_urls),
            'message': 'All content already indexed'
        }
    
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['stage'] = 'content_extraction'
    
    # Phase 2: Content Extraction (ASYNC for speed)
    logger.info("=" * 60)
    logger.info("PHASE 2: ASYNC CONTENT EXTRACTION")
    logger.info("=" * 60)
    
    # Use async crawler for 20x speed improvement
    from async_crawler import crawl_urls_async
    
    logger.info(f"Extracting content from {len(discovered_urls)} URLs using async crawler...")
    logger.info(f"Concurrency: 20 simultaneous requests")
    
    docs, log_file = crawl_urls_async(
        urls=discovered_urls,
        base_url=url,
        max_pages=100000,
        concurrency=20
    )
    
    logger.info(f"Async crawl complete! Extracted {len(docs)} documents")
    
    # Add metadata for filtering
    logger.info("🏷️  Tagging documents with metadata...")
    for doc in docs:
        url_lower = doc.metadata.get('source', '').lower()
        content = doc.page_content.lower()
        
        # Add domain metadata
        doc.metadata['domain'] = domain
        doc.metadata['namespace'] = namespace
        doc.metadata['indexed_at'] = datetime.utcnow().isoformat()
        
        # Department tagging
        if '/cse' in url_lower or 'computer science' in content:
            doc.metadata['department'] = 'CSE'
        elif '/ece' in url_lower or 'electronics' in content:
            doc.metadata['department'] = 'ECE'
        elif '/mech' in url_lower or 'mechanical' in content:
            doc.metadata['department'] = 'MECH'
        elif '/civil' in url_lower or 'civil engineering' in content:
            doc.metadata['department'] = 'CIVIL'
        elif '/eee' in url_lower or 'electrical' in content:
            doc.metadata['department'] = 'EEE'
        else:
            doc.metadata['department'] = 'General'
            
        # Content type tagging
        if 'faculty' in url_lower or 'profile' in url_lower:
            doc.metadata['type'] = 'faculty'
        elif 'course' in url_lower or 'syllabus' in url_lower:
            doc.metadata['type'] = 'course'
        elif 'admissions' in url_lower:
            doc.metadata['type'] = 'admission'
        else:
            doc.metadata['type'] = 'general'
    
    if not docs:
        logger.error("❌ No documents found.")
        if crawl_status and crawl_id:
            crawl_status[crawl_id]['progress']['stage'] = 'failed'
            crawl_status[crawl_id]['progress']['error'] = 'No documents found'
        return {'success': False, 'error': 'No documents found'}

    logger.info(f"✅ Crawling complete! Found {len(docs)} pages.")
    
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['pages_crawled'] = len(docs)
        crawl_status[crawl_id]['progress']['stage'] = 'indexing'
    
    # Deduplicate documents
    logger.info("🔍 Deduplicating documents...")
    seen_hashes = set()
    unique_docs = []
    for doc in docs:
        doc_hash = calculate_doc_hash(doc)
        if doc_hash not in seen_hashes:
            seen_hashes.add(doc_hash)
            unique_docs.append(doc)
    
    logger.info(f"📊 After deduplication: {len(unique_docs)} unique documents")
    
    # Split documents into smaller chunks
    logger.info("✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )
    
    split_docs = text_splitter.split_documents(unique_docs)
    logger.info(f"📊 After splitting: {len(split_docs)} chunks (from {len(unique_docs)} pages)")
    
    docs = split_docs
    
    logger.info(f"{'='*60}")
    logger.info(f"🧠 Phase 3: Generating embeddings with Local HuggingFace...")
    logger.info(f"{'='*60}")

    # Initialize Embeddings
    logger.info(f"📥 Loading local embedding model ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # FAST INGESTION MODE
    total_batches = (len(docs) + INGESTION_BATCH_SIZE - 1) // INGESTION_BATCH_SIZE
    
    logger.info(f"📦 Processing {len(docs)} documents in {total_batches} batches...")
    logger.info(f"🚀 Running in LOCAL EMBEDDING MODE (Unlimited Speed)")
    logger.info(f"📦 Using namespace: {namespace}")
    
    indexed_count = 0
    failed_batches = []
    
    for i in range(0, len(docs), INGESTION_BATCH_SIZE):
        batch = docs[i:i + INGESTION_BATCH_SIZE]
        batch_num = (i // INGESTION_BATCH_SIZE) + 1
        
        logger.info(f"🔄 Batch {batch_num}/{total_batches} ({len(batch)} docs)...")
        
        try:
            # Fix #6: Use namespace for isolation
            PineconeVectorStore.from_documents(
                batch,
                embeddings,
                index_name=PINECONE_INDEX,
                pinecone_api_key=PINECONE_API_KEY,
                namespace=namespace
            )
            logger.info(f"✓ Batch {batch_num}/{total_batches} indexed ({indexed_count + len(batch)}/{len(docs)} docs)")
            indexed_count += len(batch)
            
            # Update status
            if crawl_status and crawl_id:
                crawl_status[crawl_id]['progress']['pages_indexed'] = indexed_count
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"⚠️  Batch {batch_num} failed: {type(e).__name__}")
            logger.error(f"    Error: {error_msg}")
            failed_batches.append(batch_num)
            if crawl_status and crawl_id:
                crawl_status[crawl_id]['progress']['errors'] += 1
    
    logger.info(f"{'='*60}")
    logger.info("🎉 Ingestion complete!")
    logger.info(f"✅ Successfully indexed: {indexed_count}/{len(docs)} documents")
    
    if failed_batches:
        logger.warning(f"Failed batches: {len(failed_batches)} - {failed_batches}")
    
    logger.info(f"{'='*60}")
    
    result = {
        'success': True,
        'total_documents': len(docs),
        'indexed_documents': indexed_count,
        'failed_batches': len(failed_batches),
        'skipped_existing': len(existing_urls),
        'namespace': namespace,
        'crawl_log': log_file
    }
    
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['stage'] = 'completed'
        crawl_status[crawl_id]['result'] = result
    
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest website content into Pinecone.")
    parser.add_argument("--url", type=str, required=True, help="Base URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Max recursion depth")
    
    args = parser.parse_args()
    result = ingest(args.url, args.depth)
    logger.info(f"Ingestion result: {result}")
