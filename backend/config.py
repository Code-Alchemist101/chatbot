import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
MONGO_URI = os.getenv("MONGO_URI")

# Validation
if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env")
if not PINECONE_API_KEY or not PINECONE_INDEX:
    raise ValueError("Missing PINECONE_API_KEY or PINECONE_INDEX in .env")

# Crawling Configuration
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "30"))
MAX_URLS = int(os.getenv("MAX_URLS", "100000"))
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", "15"))
MIN_CRAWL_DEPTH = 1
MAX_CRAWL_DEPTH = 5
DEFAULT_CRAWL_DEPTH = 2

# Chunking Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
EMBEDDING_DIMENSION = 768

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

# RAG Configuration
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "8"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# Rate Limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Crawl Status Management
MAX_CRAWL_HISTORY = int(os.getenv("MAX_CRAWL_HISTORY", "100"))
CRAWL_CLEANUP_INTERVAL = int(os.getenv("CRAWL_CLEANUP_INTERVAL", "300"))  # 5 minutes

# Batch Processing
INGESTION_BATCH_SIZE = int(os.getenv("INGESTION_BATCH_SIZE", "50"))

# MongoDB Configuration
DB_NAME = "klbot_chat"
COLLECTION_NAME = "chat_history"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "chatbot.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Flask Configuration
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
