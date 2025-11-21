import os
import argparse
import time
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from crawler import RecursiveCrawler

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

def ingest(url, max_depth=2):
    print(f"\n{'='*60}")
    print(f"🚀 Starting ingestion for: {url}")
    print(f"📊 Max depth: {max_depth}")
    print(f"{'='*60}\n")
    
    # Crawl
    print("🕷️  Phase 1: Crawling website...")
    crawler = RecursiveCrawler(url, max_depth=max_depth)
    docs = crawler.start()
    
    if not docs:
        print("❌ No documents found.")
        return

    print(f"\n✅ Crawling complete! Found {len(docs)} pages.")
    print(f"\n{'='*60}")
    print(f"🧠 Phase 2: Generating embeddings with Gemini AI...")
    print(f"{'='*60}\n")

    # Initialize Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", 
        google_api_key=GOOGLE_API_KEY
    )

    # Process in batches to avoid rate limits
    batch_size = 5  # Reduced from 10 to 5
    total_batches = (len(docs) + batch_size - 1) // batch_size
    
    print(f"📦 Processing {len(docs)} documents in {total_batches} batches...")
    print(f"⚠️  Using 5-second delays to avoid rate limits")
    
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
            print(f"✓ Batch {batch_num} indexed successfully")
            
            # Rate limiting: wait between batches (increased to 5 seconds)
            if i + batch_size < len(docs):
                print("⏳ Waiting 5 seconds to avoid rate limits...")
                time.sleep(5)
                
        except Exception as e:
            error_details = f"Error type: {type(e).__name__}, Message: {str(e)}"
            print(f"✗ Error indexing batch {batch_num}: {error_details}")
            
            if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                print("⚠️  Rate limit hit. Waiting 10 seconds...")
                time.sleep(10)
                # Retry once
                try:
                    PineconeVectorStore.from_documents(
                        batch,
                        embeddings,
                        index_name=PINECONE_INDEX,
                        pinecone_api_key=PINECONE_API_KEY
                    )
                    print(f"✓ Batch {batch_num} indexed successfully (retry)")
                except Exception as retry_error:
                    print(f"✗ Retry failed: {type(retry_error).__name__}: {str(retry_error)}")
            else:
                print(f"⚠️  Skipping batch {batch_num} due to error. Continuing with next batch...")
                continue
    
    print(f"\n{'='*60}")
    print("🎉 Ingestion complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest website content into Pinecone.")
    parser.add_argument("--url", type=str, required=True, help="Base URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Max recursion depth")
    
    args = parser.parse_args()
    ingest(args.url, args.depth)
