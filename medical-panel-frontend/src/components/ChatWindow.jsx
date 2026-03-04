import React, { useState, useRef, useEffect } from 'react';

const SendIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 2L11 13" /><path d="M22 2L15 22 11 13 2 9l20-7z" />
    </svg>
);

const SUGGESTIONS = [
    'I have chest pain and shortness of breath',
    'My skin has an itchy rash for 3 days',
    'I have severe headaches and blurry vision',
];

export default function ChatWindow({ messages, isLoading, onSendMessage, activeTheme, activeSpecialists, specialists }) {
    const [input, setInput] = useState('');
    const bottomRef = useRef(null);
    const textareaRef = useRef(null);
    const isSolo = activeSpecialists && activeSpecialists.length === 1;
    const soloSpec = isSolo && specialists ? specialists.find(s => s.id === activeSpecialists[0]) : null;

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const resize = () => {
        const ta = textareaRef.current;
        if (!ta) return;
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 150) + 'px';
    };

    const send = () => {
        const text = input.trim();
        if (text && !isLoading) {
            onSendMessage(text);
            setInput('');
            if (textareaRef.current) textareaRef.current.style.height = '22px';
        }
    };

    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    };

    return (
        <div className="chat-area">
            {/* Top bar */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '12px 24px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                background: '#111',
                flexShrink: 0,
            }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: 'rgba(255,255,255,0.5)' }}>🩺 Medical Panel</span>
                {soloSpec && (
                    <span className="accent-bg-subtle accent-text accent-transition" style={{
                        marginLeft: 'auto', fontSize: 11, fontWeight: 600,
                        padding: '3px 10px', borderRadius: 999,
                    }}>
                        {soloSpec.name}
                    </span>
                )}
            </div>

            {/* Messages */}
            <div className="chat-messages scrollbar-thin">
                <div className="chat-inner">

                    {/* Empty state */}
                    {messages.length === 0 && !isLoading && (
                        <div style={{ textAlign: 'center', paddingTop: 60, paddingBottom: 40 }}>
                            <div style={{
                                width: 52, height: 52, borderRadius: 16,
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 22, margin: '0 auto 18px',
                            }}>🩺</div>
                            <h2 style={{ fontSize: 20, fontWeight: 600, color: 'rgba(255,255,255,0.85)', marginBottom: 10 }}>
                                Medical Panel Assistant
                            </h2>
                            <p style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.33)', maxWidth: 380, margin: '0 auto 28px', lineHeight: 1.65 }}>
                                Describe your symptoms. Our panel of specialists will evaluate your case and narrow down to the right doctor.
                            </p>
                            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8 }}>
                                {SUGGESTIONS.map(s => (
                                    <button key={s} className="chip" onClick={() => onSendMessage(s)}>{s}</button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Message list */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                        {messages.map((msg, idx) => (
                            <div key={idx} className="msg-in" style={{
                                display: 'flex',
                                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                                alignItems: 'flex-start',
                                gap: 10,
                            }}>
                                {/* Avatar */}
                                <div className="avatar-circle accent-transition" style={{
                                    background: msg.role === 'user'
                                        ? 'rgba(255,255,255,0.09)'
                                        : 'var(--color-accent-subtle)',
                                    color: msg.role === 'user'
                                        ? 'rgba(255,255,255,0.6)'
                                        : 'var(--color-accent-text)',
                                    fontWeight: 600, fontSize: 13,
                                }}>
                                    {msg.role === 'user' ? 'U' : '🩺'}
                                </div>

                                {/* Bubble */}
                                <div className={msg.role === 'user' ? 'bubble-user' : 'bubble-ai'}>
                                    {msg.content.split('\n').map((line, i, arr) => (
                                        <React.Fragment key={i}>
                                            {line}{i < arr.length - 1 && <br />}
                                        </React.Fragment>
                                    ))}
                                </div>
                            </div>
                        ))}

                        {/* Typing dots */}
                        {isLoading && (
                            <div className="msg-in" style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                                <div className="avatar-circle accent-bg-subtle accent-text accent-transition">🩺</div>
                                <div className="bubble-ai" style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '14px 18px' }}>
                                    <span className="typing-dot" />
                                    <span className="typing-dot" />
                                    <span className="typing-dot" />
                                </div>
                            </div>
                        )}
                    </div>
                    <div ref={bottomRef} />
                </div>
            </div>

            {/* Input bar */}
            <div style={{ flexShrink: 0, padding: '12px 24px 20px' }}>
                <div style={{ maxWidth: 680, margin: '0 auto' }}>
                    <div className="input-bar">
                        <textarea
                            ref={textareaRef}
                            rows={1}
                            value={input}
                            onChange={(e) => { setInput(e.target.value); resize(); }}
                            onKeyDown={handleKey}
                            placeholder="Describe your symptoms…"
                            disabled={isLoading}
                            style={{ height: 22 }}
                        />
                        <button
                            className="send-btn accent-transition"
                            onClick={send}
                            disabled={!input.trim() || isLoading}
                            style={{
                                background: input.trim() && !isLoading
                                    ? 'var(--color-accent)'
                                    : 'rgba(255,255,255,0.07)',
                                color: input.trim() && !isLoading
                                    ? '#fff'
                                    : 'rgba(255,255,255,0.25)',
                            }}
                        >
                            <SendIcon />
                        </button>
                    </div>
                    <p style={{ textAlign: 'center', fontSize: 11, color: 'rgba(255,255,255,0.16)', marginTop: 8 }}>
                        For demonstration only — not a substitute for professional medical advice.
                    </p>
                </div>
            </div>
        </div>
    );
}
