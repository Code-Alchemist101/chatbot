import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Loader2, Globe, Bot, ArrowLeft, MessageSquare, Plus, Menu, X } from 'lucide-react';
import MessageBubble from './MessageBubble';

const ChatInterface = ({ selectedBot, onBack, isWidget = false }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const messagesEndRef = useRef(null);

    // Initialize session on load
    useEffect(() => {
        if (selectedBot) {
            startNewSession();
            fetchSessions();
        }
    }, [selectedBot]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const fetchSessions = async () => {
        if (!selectedBot) return;
        try {
            const response = await axios.get(`http://localhost:5000/api/bots/${selectedBot.id}/sessions`);
            setSessions(response.data.sessions || []);
        } catch (error) {
            console.error("Error fetching sessions:", error);
        }
    };

    const startNewSession = () => {
        setSessionId('session-' + Date.now());
        setMessages([]);
    };

    const loadSession = async (sid) => {
        setSessionId(sid);
        try {
            const response = await axios.get(`http://localhost:5000/api/history?session_id=${sid}`);
            setMessages(response.data.messages || []);
        } catch (error) {
            console.error("Error loading session:", error);
        }
    };

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        // Create a placeholder for the AI message
        const aiMessageId = Date.now();
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            id: aiMessageId
        }]);

        try {
            // Prepare history for context (last 6 messages)
            const historyContext = messages.slice(-6).map(m => ({
                role: m.role,
                content: m.content
            }));

            const response = await fetch('http://localhost:5000/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: userMessage.content,
                    session_id: sessionId,
                    namespace: selectedBot?.namespace,
                    bot_id: selectedBot?.id,
                    history: historyContext
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let aiContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            // Refresh sessions list to show new chat
                            fetchSessions();
                            break;
                        }
                        if (data.startsWith('Error:')) {
                            aiContent += "\n\n*Error: " + data.slice(6) + "*";
                        } else {
                            aiContent += data;
                        }

                        setMessages(prev => prev.map(msg =>
                            msg.id === aiMessageId ? { ...msg, content: aiContent } : msg
                        ));
                    }
                }
            }
        } catch (error) {
            console.error("Error sending message:", error);
            setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId ? { ...msg, content: "Sorry, I encountered an error. Please try again." } : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-gray-900 text-white overflow-hidden">
            {/* Sidebar */}
            <div className={`${isSidebarOpen ? 'w-64' : 'w-0'} bg-gray-800 transition-all duration-300 flex flex-col border-r border-gray-700`}>
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="font-bold text-gray-300 truncate">{selectedBot?.name}</h2>
                    <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-400">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-4">
                    <button
                        onClick={startNewSession}
                        className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded-lg transition-colors"
                    >
                        <Plus size={18} /> New Chat
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-2">
                    {sessions.map((session) => (
                        <button
                            key={session._id}
                            onClick={() => loadSession(session._id)}
                            className={`w-full text-left p-3 rounded-lg text-sm transition-colors flex items-center gap-2 ${sessionId === session._id ? 'bg-gray-700 text-white' : 'text-gray-400 hover:bg-gray-700/50'
                                }`}
                        >
                            <MessageSquare size={16} />
                            <span className="truncate">
                                {session.preview?.substring(0, 30) || "New Conversation"}...
                            </span>
                        </button>
                    ))}
                </div>

                <div className="p-4 border-t border-gray-700">
                    <button
                        onClick={onBack}
                        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft size={18} /> Back to Dashboard
                    </button>
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col h-full relative">
                {/* Header */}
                <header className="bg-gray-800 p-4 shadow-lg flex items-center gap-4 z-10">
                    {!isSidebarOpen && (
                        <button onClick={() => setIsSidebarOpen(true)} className="text-gray-400 hover:text-white">
                            <Menu size={24} />
                        </button>
                    )}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-tr from-blue-400 to-purple-500 rounded-lg flex items-center justify-center font-bold text-lg">
                            {selectedBot?.name?.[0] || 'B'}
                        </div>
                        <div>
                            <h1 className="font-bold text-white">{selectedBot?.name}</h1>
                            <p className="text-xs text-gray-400">{selectedBot?.url}</p>
                        </div>
                    </div>
                </header>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-gray-900">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-50">
                            <div className="w-16 h-16 bg-gray-800 rounded-2xl mb-4 flex items-center justify-center">
                                <Bot size={32} />
                            </div>
                            <p>Ask anything about {selectedBot?.name}</p>
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

                {/* Input */}
                <div className="p-4 bg-gray-800 border-t border-gray-700">
                    <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={`Message ${selectedBot?.name}...`}
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
        </div>
    );
};

export default ChatInterface;
