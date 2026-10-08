import { useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiUrl } from '../config';

export const Chatbot = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const onSend = async () => {
        if (!input.trim()) return;
        const newMsg = { role: 'user', content: input };
        const updated = [...messages, newMsg];
        setMessages(updated);
        setInput('');
        setLoading(true);

        try {
            const res = await fetch(apiUrl('/api/chat'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: updated })
            });
            const data = await res.json();
            setMessages([...updated, { role: 'assistant', content: data.reply }]);
        } catch {
            setMessages([...updated, { role: 'assistant', content: 'Connection failed.' }]);
        }
        setLoading(false);
    };

    return (
        <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999 }}>
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="btn btn-primary"
                    style={{ borderRadius: '50%', width: 56, height: 56, padding: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)' }}
                >
                    <MessageCircle size={28} />
                </button>
            )}

            {isOpen && (
                <div className="card" style={{ width: 350, height: 450, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', boxShadow: 'var(--shadow-lg)' }}>
                    <div style={{ backgroundColor: 'var(--primary-color)', color: 'white', padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ fontWeight: 600 }}>Groq AI Assistant</div>
                        <button onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}><X size={20} /></button>
                    </div>

                    <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', backgroundColor: '#fafafa', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {messages.length === 0 && <div className="text-muted text-sm text-center mt-4">Ask me anything about your proposals or RocketRide!</div>}
                        {messages.map((m, i) => (
                            <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', backgroundColor: m.role === 'user' ? 'var(--primary-color)' : 'white', color: m.role === 'user' ? 'white' : 'black', padding: '8px 12px', borderRadius: '8px', maxWidth: '80%', fontSize: '0.875rem', border: m.role === 'assistant' ? '1px solid #ddd' : 'none' }}>
                                {m.role === 'assistant' ? (
                                    <div className="markdown-body" style={{ display: 'flex', flexDirection: 'column', gap: '6px', margin: 0 }}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                                    </div>
                                ) : (
                                    m.content
                                )}
                            </div>
                        ))}
                        {loading && <div className="text-muted text-xs">AI is typing...</div>}
                    </div>

                    <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '8px', backgroundColor: 'white' }}>
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && onSend()}
                            placeholder="Type a message..."
                            style={{ flex: 1, padding: '8px 12px', borderRadius: '4px', border: '1px solid var(--border-color)' }}
                        />
                        <button className="btn btn-primary" style={{ padding: '8px 12px' }} onClick={onSend} disabled={loading}><Send size={16} /></button>
                    </div>
                </div>
            )}
        </div>
    );
};
