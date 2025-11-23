import React, { useState } from 'react';
import Onboarding from './components/Onboarding';
import ChatInterface from './components/ChatInterface';
import BotDashboard from './components/BotDashboard';

function App() {
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'onboarding' | 'chat'
  const [selectedBot, setSelectedBot] = useState(null);

  const handleSelectBot = (bot) => {
    setSelectedBot(bot);
    setView('chat');
  };

  const handleCreateNew = () => {
    setView('onboarding');
  };

  const handleOnboardingComplete = () => {
    // After crawling, go back to dashboard to see the new bot
    // Or we could auto-select it if we had the ID
    setView('dashboard');
  };

  const handleBackToDashboard = () => {
    setView('dashboard');
    setSelectedBot(null);
  };

  return (
    <div className="App">
      {view === 'dashboard' && (
        <BotDashboard
          onSelectBot={handleSelectBot}
          onCreateNew={handleCreateNew}
        />
      )}

      {view === 'onboarding' && (
        <Onboarding onComplete={handleOnboardingComplete} />
      )}

      {view === 'chat' && (
        <ChatInterface
          selectedBot={selectedBot}
          onBack={handleBackToDashboard}
        />
      )}
    </div>
  );
}

export default App;
