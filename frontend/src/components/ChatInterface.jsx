import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Loader2, Globe, Bot } from 'lucide-react';
import MessageBubble from './MessageBubble';

const ChatInterface = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState('session-' + Date.now());
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await axios.post('http://localhost:5000/api/chat', {
                question: userMessage.content,
                session_id: sessionId
            });

            const aiMessage = {
                role: 'assistant',
                content: response.data.answer,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            console.error("Error sending message:", error);
            const errorMessage = {
                role: 'assistant',
                content: "Sorry, I encountered an error. Please try again.",
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCrawl = async () => {
        const url = prompt("Enter URL to crawl (e.g., https://www.kluniversity.in):");
        if (url) {
            try {
                await axios.post('http://localhost:5000/api/crawl', { url });
                alert(`Started crawling ${url}. This may take a while.`);
            } catch (error) {
                alert("Error starting crawl.");
            }
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-900 text-white">
            {/* Header */}
            <header className="bg-gray-800 p-4 shadow-lg flex justify-between items-center z-10">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-gradient-to-tr from-blue-400 to-purple-500 rounded-lg flex items-center justify-center font-bold text-lg">
                        S
                    </div>
                    <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                        Skytrade AI
                    </h1>
                </div>
                <button
                    onClick={handleCrawl}
                    className="p-2 bg-gray-700 hover:bg-gray-600 rounded-full transition-colors"
                    title="Crawl new URL"
                >
                    <Globe size={20} />
                </button>
            </header>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50">
                        <div className="w-16 h-16 bg-gray-800 rounded-2xl mb-4 flex items-center justify-center">
                            <Bot size={32} />
                        </div>
                        <p>Start a conversation with Skytrade AI</p>
                    </div>
                )}
                {messages.map((msg, index) => (
                    <MessageBubble key={index} message={msg} />
                ))}
                {isLoading && (
                    <div className="flex justify-start mb-4">
                        <div className="bg-gray-800 p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
                            <Loader2 size={16} className="animate-spin text-purple-400" />
                            <span className="text-gray-400 text-sm">Thinking...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-gray-800 border-t border-gray-700">
                <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask me anything..."
                        className="w-full bg-gray-900 text-white rounded-full pl-6 pr-12 py-4 focus:outline-none focus:ring-2 focus:ring-purple-500 border border-gray-700 transition-all shadow-inner"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2 top-2 p-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-full transition-all shadow-lg"
                    >
                        <Send size={20} className="text-white" />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ChatInterface;
