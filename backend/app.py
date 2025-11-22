crawl_status = {}

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    session_id = data.get('session_id', 'default')

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if len(question.strip()) < 3:
        return jsonify({"error": "Question too short"}), 400

    if len(question) > 1000:
        return jsonify({"error": "Question too long (max 1000 characters)"}), 400

    try:
        # Save user message
        db.save_message(session_id, "user", question)

        # Generate answer with timeout
        answer = get_answer(question)

        if not answer or answer.strip() == "":
            answer = "I couldn't generate a response. Please try rephrasing your question."

        # Save AI message
        db.save_message(session_id, "assistant", answer)

        return jsonify({"answer": answer})
    
    except Exception as e:
        error_msg = "I'm having trouble processing your request. Please try again."
        print(f"Error in chat: {str(e)}")
        db.save_message(session_id, "assistant", error_msg)
        return jsonify({"answer": error_msg})

@app.route('/api/history', methods=['GET'])
def history():
    session_id = request.args.get('session_id', 'default')
    try:
        messages = db.get_history(session_id)
        return jsonify({"messages": messages})
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        return jsonify({"messages": []})

@app.route('/api/crawl', methods=['POST'])
def crawl():
    print("\n" + "="*60)
    print("🌐 Crawl endpoint called!")
    print("="*60)
    
    data = request.json
    url = data.get('url')
    depth = data.get('depth', 2)
    
    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Validate URL
    if not url.startswith(('http://', 'https://')):
        return jsonify({"error": "Invalid URL format"}), 400

    # Check if already crawling
    if url in crawl_status and crawl_status[url]['status'] == 'running':
        return jsonify({
            "error": "Already crawling this URL",
            "status": crawl_status[url]
        }), 409

    # Initialize crawl status
    crawl_id = f"{url}_{int(time.time())}"
    crawl_status[crawl_id] = {
        'url': url,
        'status': 'running',
        'started_at': datetime.utcnow().isoformat(),
        'progress': {
            'pages_crawled': 0,
            'pages_indexed': 0,
            'errors': 0
        }
    }

    # Run ingestion in background
    def crawl_with_status(url, depth, crawl_id):
        try:
            result = ingest(url, depth, crawl_id, crawl_status)
            crawl_status[crawl_id]['status'] = 'completed'
            crawl_status[crawl_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
            crawl_status[crawl_id]['result'] = result
        except Exception as e:
            crawl_status[crawl_id]['status'] = 'failed'
            crawl_status[crawl_id]['error'] = str(e)
            print(f"❌ Crawl failed: {str(e)}")

    thread = threading.Thread(target=crawl_with_status, args=(url, depth, crawl_id))
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": f"Started crawling {url}",
        "crawl_id": crawl_id,
        "status_url": f"/api/crawl/status/{crawl_id}"
    })

@app.route('/api/crawl/status/<crawl_id>', methods=['GET'])
def crawl_status_endpoint(crawl_id):
    if crawl_id not in crawl_status:
        return jsonify({"error": "Crawl ID not found"}), 404
    
    return jsonify(crawl_status[crawl_id])

@app.route('/api/crawl/active', methods=['GET'])
def active_crawls():
    active = {k: v for k, v in crawl_status.items() if v['status'] == 'running'}
    return jsonify({"active_crawls": active})

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)