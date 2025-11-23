import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, MessageSquare, Globe, Loader2 } from 'lucide-react';

const BotDashboard = ({ onSelectBot, onCreateNew }) => {
    const [bots, setBots] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchBots();
    }, []);

    const fetchBots = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/bots');
            setBots(response.data.bots || []);
        } catch (err) {
            console.error("Error fetching bots:", err);
            setError("Failed to load bots. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-screen bg-gray-100">
                <Loader2 className="w-10 h-10 animate-spin text-purple-600" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100 p-8">
            <div className="max-w-6xl mx-auto">
                <header className="mb-12 text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">Your AI Chatbots</h1>
                    <p className="text-xl text-gray-600">Select a bot to start chatting or create a new one.</p>
                </header>

                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-8 text-center">
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {/* Create New Bot Card */}
                    <button
                        onClick={onCreateNew}
                        className="group flex flex-col items-center justify-center h-64 bg-white rounded-2xl shadow-md hover:shadow-xl border-2 border-dashed border-gray-300 hover:border-purple-500 transition-all duration-300"
                    >
                        <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-purple-600 transition-colors">
                            <Plus className="w-8 h-8 text-purple-600 group-hover:text-white" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-800 group-hover:text-purple-600">Create New Bot</h3>
                        <p className="text-gray-500 mt-2">Crawl a new website</p>
                    </button>

                    {/* Existing Bots */}
                    {bots.map((bot) => (
                        <div
                            key={bot.id}
                            onClick={() => onSelectBot(bot)}
                            className="bg-white rounded-2xl shadow-md hover:shadow-xl cursor-pointer transition-all duration-300 overflow-hidden border border-gray-100 hover:border-purple-200 group"
                        >
                            <div className="h-32 bg-gradient-to-br from-blue-500 to-purple-600 p-6 flex flex-col justify-between relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-150"></div>
                                <div className="flex justify-between items-start z-10">
                                    <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                                        <Globe className="w-6 h-6 text-white" />
                                    </div>
                                    <span className="text-xs font-medium bg-black/20 text-white px-2 py-1 rounded-full backdrop-blur-sm">
                                        {new Date(bot.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <h3 className="text-xl font-bold text-white truncate z-10">{bot.name}</h3>
                            </div>
                            <div className="p-6">
                                <p className="text-gray-500 text-sm mb-4 truncate">{bot.url}</p>
                                <div className="flex items-center text-purple-600 font-medium group-hover:translate-x-2 transition-transform">
                                    <MessageSquare className="w-4 h-4 mr-2" />
                                    Start Chatting
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default BotDashboard;
