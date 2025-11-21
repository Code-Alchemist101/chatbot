from flask import Flask, request, jsonify
from flask_cors import CORS
from rag import get_answer
from db import db
from ingest import ingest
import threading

app = Flask(__name__)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    session_id = data.get('session_id', 'default')

    if not question:
        return jsonify({"error": "Question is required"}), 400

    # Save user message
    db.save_message(session_id, "user", question)

    # Generate answer
    answer = get_answer(question)

    # Save AI message
    db.save_message(session_id, "assistant", answer)

    return jsonify({"answer": answer})

@app.route('/api/history', methods=['GET'])
def history():
    session_id = request.args.get('session_id', 'default')
    messages = db.get_history(session_id)
    return jsonify({"messages": messages})

@app.route('/api/crawl', methods=['POST'])
def crawl():
    print("\n" + "="*60)
    print("🌐 Crawl endpoint called!")
    print("="*60)
    
    data = request.json
    url = data.get('url')
    depth = data.get('depth', 2)
    
    print(f"📍 URL: {url}")
    print(f"📊 Depth: {depth}")

    if not url:
        print("❌ Error: No URL provided")
        return jsonify({"error": "URL is required"}), 400

    # Run ingestion in background
    print("🚀 Starting background thread for ingestion...")
    thread = threading.Thread(target=ingest, args=(url, depth))
    thread.start()
    
    print(f"✅ Thread started successfully")
    print("="*60 + "\n")

    return jsonify({"message": f"Started crawling {url} with depth {depth}"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
