import React, { useState, useEffect } from 'react';
// Global logging utility
const log = (...args) => { console.log('[App]', ...args); };
const warn = (...args) => { console.warn('[App]', ...args); };
const error = (...args) => { console.error('[App]', ...args); };
import ChatWindow from './components/ChatWindow';
import SpecialistPanel from './components/SpecialistPanel';

function App() {
  const [specialists, setSpecialists] = useState([]);
  const [isLoadingSpecs, setIsLoadingSpecs] = useState(true);
  const [activeSpecialists, setActiveSpecialists] = useState([]);
  const [activeTheme, setActiveTheme] = useState('cmo');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch specialists on mount
  useEffect(() => {
    const fetchSpecialists = async () => {
      try {
        log('Fetching specialists...');
        const res = await fetch('http://localhost:8000/api/specialists');
        if (!res.ok) throw new Error('Failed to fetch specialists');
        const data = await res.json();
        log('Fetched specialists:', data);
        setSpecialists(data);
        setActiveSpecialists(data.map(s => s.id));
      } catch (err) {
        error('Error fetching specialists:', err);
        setError('Could not connect to the Medical Panel backend. Please ensure the server is running.');
      } finally {
        log('Finished fetching specialists.');
        setIsLoadingSpecs(false);
      }
    };
    fetchSpecialists();
  }, []);

  // Dynamic theme: switch when one specialist remains
  useEffect(() => {
    log('Active specialists changed:', activeSpecialists);
    if (activeSpecialists.length === 1 && specialists.length > 0) {
      const remaining = specialists.find(s => s.id === activeSpecialists[0]);
      if (remaining) {
        log('Switching theme to', remaining.theme);
        setActiveTheme(remaining.theme);
      }
    } else if (activeSpecialists.length > 1) {
      log('Switching theme to cmo');
      setActiveTheme('cmo');
    }
  }, [activeSpecialists, specialists]);

  const handleSendMessage = async (content) => {
    const userMsg = { role: 'user', content };
    const newMessages = [...messages, userMsg];
    log('User sent message:', content);
    setMessages(newMessages);
    setIsLoading(true);

    try {
      log('Sending chat to backend:', { messages: newMessages, active_specialists: activeSpecialists });
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages, active_specialists: activeSpecialists }),
      });
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      log('Received response from backend:', data);
      setMessages([...newMessages, { role: 'assistant', content: data.response }]);
      setActiveSpecialists(data.active_specialists);
    } catch (err) {
      error('Error sending message:', err);
      setMessages([...newMessages, {
        role: 'assistant',
        content: "I'm sorry, I'm having trouble connecting to the panel right now.",
      }]);
    } finally {
      log('Finished sending chat.');
      setIsLoading(false);
    }
  };

  /* ── Loading screen ──────────────────────────────────────────────── */
  if (isLoadingSpecs) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-[#0d0d0d] gap-4">
        <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-xl animate-pulse">
          🩺
        </div>
        <p className="text-sm text-white/30">Connecting to Medical Panel…</p>
      </div>
    );
  }

  /* ── Error screen ────────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-[#0d0d0d]">
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl max-w-sm text-center">
          <p className="text-lg mb-1">⚠️ Connection Error</p>
          <p className="text-sm opacity-70">{error}</p>
        </div>
      </div>
    );
  }

  /* ── Main layout ─────────────────────────────────────────────────── */
  return (
    <div
      className={`theme-${activeTheme}`}
      style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden' }}
    >
      {/* Left sidebar */}
      <SpecialistPanel
        specialists={specialists}
        activeSpecs={activeSpecialists}
      />

      {/* Right — chat */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        activeTheme={activeTheme}
        activeSpecialists={activeSpecialists}
        specialists={specialists}
      />
    </div>
  );
}

export default App;
