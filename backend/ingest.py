import os
import argparse
import time
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from crawler import RecursiveCrawler
import hashlib

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

def calculate_doc_hash(doc):
    """Calculate hash of document content for deduplication"""
    content = doc.page_content + str(doc.metadata.get('source', ''))
    return hashlib.md5(content.encode()).hexdigest()

def ingest(url, max_depth=2, crawl_id=None, crawl_status=None):
    print(f"\n{'='*60}")
    print(f"🚀 Starting ingestion for: {url}")
    print(f"📊 Max depth: {max_depth}")
    print(f"{'='*60}\n")
    
    # Update status
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['stage'] = 'crawling'
    
    # Crawl
    print("🕷️  Phase 1: Crawling website...")
    crawler = RecursiveCrawler(url, max_depth=max_depth, max_pages=2000)
    docs = crawler.start()
    
    if not docs:
        print("❌ No documents found.")
        if crawl_status and crawl_id:
            crawl_status[crawl_id]['progress']['stage'] = 'failed'
            crawl_status[crawl_id]['progress']['error'] = 'No documents found'
        return {'success': False, 'error': 'No documents found'}

    print(f"\n✅ Crawling complete! Found {len(docs)} pages.")
    
    if crawl_status and crawl_id:
        crawl_status[crawl_id]['progress']['pages_crawled'] = len(docs)
        crawl_status[crawl_id]['progress']['stage'] = 'indexing'
    
    # Deduplicate documents
    print("\n🔍 Deduplicating documents...")
    seen_hashes = set()
    unique_docs = []
    for doc in docs:
        doc_hash = calculate_doc_hash(doc)
        if doc_hash not in seen_hashes:
            seen_hashes.add(doc_hash)
            unique_docs.append(doc)
    
    print(f"📊 After deduplication: {len(unique_docs)} unique documents")
    
    # Split documents into smaller chunks to avoid Pinecone metadata limits (40KB)
    # and improve RAG retrieval quality
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    print("\n✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    
    split_docs = text_splitter.split_documents(unique_docs)
    print(f"📊 After splitting: {len(split_docs)} chunks (from {len(unique_docs)} pages)")
    
    docs = split_docs
    
    print(f"\n{'='*60}")
    print(f"🧠 Phase 2: Generating embeddings with Local HuggingFace...")
    print(f"{'='*60}\n")

    # Initialize Embeddings
    # Using Local HuggingFace Embeddings (No Rate Limits!)
    # model_name="all-mpnet-base-v2" produces 768-dimensional vectors, matching Gemini/Pinecone requirements
    from langchain_huggingface import HuggingFaceEmbeddings
    
    print("📥 Loading local embedding model (all-mpnet-base-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    # FAST INGESTION MODE (Local Embeddings)
    # No API rate limits, so we can process faster!
    batch_size = 50  # Larger batch size for efficiency
    total_batches = (len(docs) + batch_size - 1) // batch_size
    
    print(f"📦 Processing {len(docs)} documents in {total_batches} batches...")
    print(f"🚀 Running in LOCAL EMBEDDING MODE (Unlimited Speed)")
    
    indexed_count = 0
    failed_batches = []
    
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"\n🔄 Batch {batch_num}/{total_batches} ({len(batch)} docs)...")
        
        try:
            PineconeVectorStore.from_documents(
                batch,
                embeddings,
                index_name=PINECONE_INDEX,
                pinecone_api_key=PINECONE_API_KEY
            )
            print(f"✓ Batch {batch_num}/{total_batches} indexed ({indexed_count + len(batch)}/{len(docs)} docs)")
            indexed_count += len(batch)
            
            # Update status
            if crawl_status and crawl_id:
                crawl_status[crawl_id]['progress']['pages_indexed'] = indexed_count
                
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Batch {batch_num} failed: {type(e).__name__}")
            print(f"    Error: {error_msg}")
            failed_batches.append(batch_num)
            if crawl_status and crawl_id:
                crawl_status[crawl_id]['progress']['errors'] += 1
    
    print(f"\n{'='*60}")
    print("🎉 Ingestion complete!")
    print(f"✅ Successfully indexed: {indexed_count}/{len(docs)} documents")
    
    if failed_batches:
        print(f"⚠️  Failed batches: {len(failed_batches)} - {failed_batches}")
    
    print(f"{'='*60}\n")
    
    result = {
        'success': True,
        'total_documents': len(docs),
        'indexed_documents': indexed_count,
        'failed_batches': len(failed_batches),
        'crawl_log': crawler.log_file
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
    print(f"\nIngestion result: {result}")
