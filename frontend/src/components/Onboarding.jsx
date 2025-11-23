import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

const Onboarding = ({ onComplete }) => {
    const [url, setUrl] = useState('');
    const [depth, setDepth] = useState(2);
    const [status, setStatus] = useState('idle'); // idle, crawling, completed, error
    const [crawlId, setCrawlId] = useState(null);
    const [progress, setProgress] = useState({ pages: 0, indexed: 0 });
    const [error, setError] = useState('');
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    const MAX_RECONNECT_ATTEMPTS = 3;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus('crawling');
        setError('');
        setReconnectAttempts(0);

        try {
            const response = await axios.post('http://localhost:5000/api/crawl', { url, depth });
            setCrawlId(response.data.crawl_id);
        } catch (err) {
            setStatus('error');
            setError(err.response?.data?.error || 'Failed to start crawling. Is the backend running?');
        }
    };

    // Fix #3: EventSource with timeout and retry logic
    useEffect(() => {
        let eventSource;
        let reconnectTimer;

        if (status === 'crawling' && crawlId) {
            const connectEventSource = () => {
                eventSource = new EventSource(`http://localhost:5000/api/crawl/stream/${crawlId}`);

                eventSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);

                        if (data.error) {
                            setStatus('error');
                            setError(data.error);
                            eventSource.close();
                            return;
                        }

                        if (data.status === 'completed') {
                            setStatus('completed');
                            eventSource.close();
                            setTimeout(() => onComplete(), 1500);
                        } else if (data.status === 'failed') {
                            setStatus('error');
                            setError(data.error || 'Crawl failed');
                            eventSource.close();
                        } else {
                            // Update progress
                            setProgress({
                                pages: data.progress?.pages_crawled || 0,
                                indexed: data.progress?.pages_indexed || 0
                            });
                            // Reset reconnect attempts on successful message
                            setReconnectAttempts(0);
                        }
                    } catch (err) {
                        console.error("Error parsing SSE data:", err);
                    }
                };

                eventSource.onerror = (err) => {
                    console.error("EventSource failed:", err);
                    eventSource.close();

                    // Implement exponential backoff retry
                    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                        const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
                        console.log(`Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);

                        reconnectTimer = setTimeout(() => {
                            setReconnectAttempts(prev => prev + 1);
                            connectEventSource();
                        }, backoffDelay);
                    } else {
                        setStatus('error');
                        setError('Connection lost. The crawl may still be running in the background. Please check back later or try refreshing.');
                    }
                };
            };

            connectEventSource();
        }

        return () => {
            if (eventSource) {
                eventSource.close();
            }
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
            }
        };
    }, [status, crawlId, onComplete, reconnectAttempts]);

    const handleRetry = () => {
        setStatus('idle');
        setError('');
        setProgress({ pages: 0, indexed: 0 });
        setCrawlId(null);
        setReconnectAttempts(0);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-gray-800 rounded-2xl shadow-2xl p-8 border border-gray-700">
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                        <span className="text-2xl font-bold text-white">AI</span>
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">RAG Chatbot</h1>
                    <p className="text-gray-400">Train your AI on any website</p>
                </div>

                {status === 'idle' && (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Website URL
                            </label>
                            <input
                                type="url"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="https://example.com"
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Crawl Depth (1-5)
                            </label>
                            <input
                                type="number"
                                min="1"
                                max="5"
                                value={depth}
                                onChange={(e) => setDepth(parseInt(e.target.value))}
                                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <button
                            type="submit"
                            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all duration-200 transform hover:scale-105"
                        >
                            Start Training
                        </button>
                    </form>
                )}

                {status === 'crawling' && (
                    <div className="text-center space-y-4">
                        <Loader2 className="w-16 h-16 text-blue-500 animate-spin mx-auto" />
                        <div>
                            <h3 className="text-xl font-semibold text-white mb-2">Training in Progress...</h3>
                            <p className="text-gray-400 text-sm mb-4">
                                {progress.pages > 0 ? `Processed ${progress.pages} pages, indexed ${progress.indexed} chunks` : 'Initializing...'}
                            </p>
                            {reconnectAttempts > 0 && (
                                <p className="text-yellow-400 text-xs">
                                    Reconnecting... (Attempt {reconnectAttempts}/{MAX_RECONNECT_ATTEMPTS})
                                </p>
                            )}
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                            <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                                style={{ width: progress.indexed > 0 ? '75%' : '25%' }}
                            />
                        </div>
                    </div>
                )}

                {status === 'completed' && (
                    <div className="text-center space-y-4">
                        <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
                        <div>
                            <h3 className="text-xl font-semibold text-white mb-2">Training Complete!</h3>
                            <p className="text-gray-400 text-sm">
                                Successfully indexed {progress.indexed} document chunks
                            </p>
                        </div>
                    </div>
                )}

                {status === 'error' && (
                    <div className="text-center space-y-4">
                        <XCircle className="w-16 h-16 text-red-500 mx-auto" />
                        <div>
                            <h3 className="text-xl font-semibold text-white mb-2">Error</h3>
                            <p className="text-red-400 text-sm mb-4">{error}</p>
                            <button
                                onClick={handleRetry}
                                className="inline-flex items-center gap-2 bg-gray-700 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-600 transition-colors"
                            >
                                <RefreshCw size={18} />
                                Try Again
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Onboarding;
