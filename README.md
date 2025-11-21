# Skytrade AI Chat Application

A full-stack RAG (Retrieval-Augmented Generation) chat application with web crawling capabilities.

## Tech Stack

### Backend
- **Framework**: Flask
- **Database**: MongoDB (chat history)
- **Vector DB**: Pinecone (embeddings)
- **AI**: Google Gemini (LLM + Embeddings)
- **Web Scraping**: BeautifulSoup + Requests

### Frontend
- **Framework**: React (Vite)
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **UI Icons**: Lucide React

## Project Structure

```
Chat-Application/
├── backend/
│   ├── app.py              # Flask API server
│   ├── db.py               # MongoDB operations
│   ├── rag.py              # RAG pipeline
│   ├── crawler.py          # Web crawler
│   ├── ingest.py           # Data ingestion
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment variables
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ChatInterface.jsx
    │   │   └── MessageBubble.jsx
    │   ├── App.jsx
    │   └── index.css
    ├── package.json        # Node dependencies
    └── vite.config.js      # Vite configuration
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (local or Atlas)
- Pinecone account
- Google AI Studio API key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX=your_index_name
MONGO_URI=mongodb://localhost:27017/
```

4. **Important**: Create Pinecone index with:
   - **Dimensions**: 768
   - **Metric**: cosine

5. Run the server:
```bash
python app.py
```

Backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Frontend will run on `http://localhost:5173`

## Usage

### 1. Ingest Data (First Time)
- Click the **Globe icon** (🌐) in the top-right
- Enter a URL to crawl (e.g., `https://example.com`)
- Wait for crawling and indexing to complete
- Check backend terminal for progress

### 2. Chat
- Type your question in the input field
- AI retrieves relevant context from Pinecone
- Gemini generates response based on context
- Chat history saved in MongoDB

## Features

- ✅ Recursive web crawling with depth control
- ✅ Automatic content filtering (skips PDFs, images)
- ✅ Rate limiting to avoid API quota issues
- ✅ Batch processing for embeddings
- ✅ Real-time progress logging
- ✅ Chat history persistence
- ✅ Markdown support in responses
- ✅ Responsive UI with Tailwind CSS

## API Endpoints

### Backend (`http://localhost:5000`)

- `GET /api/health` - Health check
- `POST /api/chat` - Send message
  ```json
  {
    "question": "What is this about?",
    "session_id": "session-123"
  }
  ```
- `GET /api/history?session_id=session-123` - Get chat history
- `POST /api/crawl` - Start crawling
  ```json
  {
    "url": "https://example.com",
    "depth": 2
  }
  ```

## Configuration

### Crawling Limits
- **Max depth**: 2 (configurable)
- **Content size**: 100 chars - 1MB
- **Batch size**: 5 documents
- **Delay between batches**: 5 seconds

### Rate Limiting
- Crawl delay: 0.5s per page
- Embedding delay: 5s per batch
- Retry delay: 10s on rate limit

## Troubleshooting

### Backend won't start
- Check `.env` file has all required keys
- Verify MongoDB is running
- Ensure Pinecone index exists with correct dimensions

### No data indexed
- Check backend terminal for errors
- Verify Gemini API key is valid
- Check Pinecone index dimensions (must be 768)

### Rate limit errors
- Increase delays in `ingest.py`
- Reduce batch size
- Use smaller crawl depth

## License

MIT
