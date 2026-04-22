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
  const [activeTheme, setActiveTheme] = useState('cmo');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [specialistResponses, setSpecialistResponses] = useState({});

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

  // Dynamic theme: always use CMO theme since all specialists respond
  useEffect(() => {
    log('Setting theme to cmo (all specialists now respond)');
    setActiveTheme('cmo');
  }, []);

  const handleSendMessage = async (content) => {
    const userMsg = { role: 'user', content };
    const newMessages = [...messages, userMsg];
    log('User sent message:', content);
    setMessages(newMessages);
    setIsLoading(true);

    try {
      log('Attempting streaming chat...');
      const response = await fetch('http://localhost:8000/api/chat-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages }),
      });
      
      if (!response.ok) throw new Error('Streaming API error');
      
      // Handle Server-Sent Events stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let hasError = false;
      const streamedResponses = {};
      let primaryResponse = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep last incomplete line in buffer
        buffer = lines[lines.length - 1];
        
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i];
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.substring(6);
              const event = JSON.parse(jsonStr);
              
              log('Stream event:', event.event);
              
              if (event.event === 'specialist_response') {
                streamedResponses[event.specialist_id] = event.response;
                setSpecialistResponses(prev => ({
                  ...prev,
                  [event.specialist_id]: event.response
                }));
              } else if (event.event === 'complete') {
                primaryResponse = event.primary_response;
                log('Stream complete, total calls:', event.total_calls);
              } else if (event.event === 'error') {
                hasError = true;
                warn('Streaming error, will fall back to regular chat:', event.message);
              }
            } catch (e) {
              error('Failed to parse stream event:', e);
            }
          }
        }
      }
      
      // If streaming succeeded with response, use it
      if (primaryResponse) {
        setMessages([...newMessages, { role: 'assistant', content: primaryResponse }]);
        setIsLoading(false);
        return;
      }
      
      // If streaming failed or no response, fall back to regular API
      if (hasError || !primaryResponse) {
        log('Streaming unavailable, falling back to regular /api/chat...');
        throw new Error('Fallback to regular API');
      }
    } catch (err) {
      // Fallback: Use regular /api/chat endpoint
      log('Falling back to regular chat endpoint:', err.message);
      try {
        const res = await fetch('http://localhost:8000/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: newMessages }),
        });
        if (!res.ok) throw new Error('Fallback API error');
        const data = await res.json();
        log('Received fallback response:', data);
        setMessages([...newMessages, { role: 'assistant', content: data.response }]);
        setSpecialistResponses(data.specialist_responses || {});
      } catch (fallbackErr) {
        error('Error in fallback chat:', fallbackErr);
        setMessages([...newMessages, {
          role: 'assistant',
          content: "I'm sorry, I'm having trouble connecting to the panel right now. Please try again in a moment.",
        }]);
      }
    } finally {
      log('Finished chat.');
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
      />

      {/* Right — chat */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        activeTheme={activeTheme}
        specialists={specialists}
        specialistResponses={specialistResponses}
      />
    </div>
  );
}

export default App;
