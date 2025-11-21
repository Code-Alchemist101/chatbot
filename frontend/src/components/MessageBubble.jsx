import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-3`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-blue-500' : 'bg-purple-600'}`}>
          {isUser ? <User size={18} className="text-white" /> : <Bot size={18} className="text-white" />}
        </div>
        
        <div className={`p-4 rounded-2xl ${isUser ? 'bg-blue-500 text-white rounded-tr-none' : 'bg-gray-800 text-gray-100 rounded-tl-none'} shadow-md`}>
          <div className="prose prose-invert max-w-none text-sm">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
          <div className={`text-xs mt-1 ${isUser ? 'text-blue-200' : 'text-gray-400'}`}>
            {new Date(message.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
