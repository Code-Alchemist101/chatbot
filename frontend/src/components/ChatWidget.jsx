import React, { useState } from 'react';
import { MessageCircle, X } from 'lucide-react';
import ChatInterface from './ChatInterface';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
            {/* Chat Window */}
            {isOpen && (
                <div className="mb-4 w-[380px] h-[600px] bg-gray-900 rounded-2xl shadow-2xl border border-gray-700 overflow-hidden flex flex-col animate-in slide-in-from-bottom-10 fade-in duration-300">
                    <div className="bg-gray-800 p-4 flex justify-between items-center border-b border-gray-700">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-gradient-to-tr from-blue-400 to-purple-500 rounded-lg flex items-center justify-center font-bold text-sm text-white">
                                AI
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">Support Assistant</h3>
                                <p className="text-xs text-green-400 flex items-center gap-1">
                                    <span className="w-2 h-2 bg-green-400 rounded-full"></span> Online
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="text-gray-400 hover:text-white transition-colors"
                        >
                            <X size={20} />
                        </button>
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <ChatInterface isWidget={true} />
                    </div>
                </div>
            )}

            {/* Toggle Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 transform hover:scale-110 ${isOpen
                        ? 'bg-gray-700 text-white rotate-90'
                        : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                    }`}
            >
                {isOpen ? <X size={24} /> : <MessageCircle size={28} />}
            </button>
        </div>
    );
};

export default ChatWidget;
