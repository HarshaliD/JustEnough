import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Minimize2, Shield, Loader2, Bot, User } from 'lucide-react';
import { sendChatMessage } from '../api';

export default function ChatPanel({ minimizedText, liveMode }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, open]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data = await sendChatMessage({
        minimizedText,
        history: messages,
        message: text,
        live: liveMode,
      });
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* FAB Button */}
      <button
        id="chat-fab-btn"
        onClick={() => setOpen(true)}
        className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white shadow-xl shadow-blue-500/30 transition-all duration-200 active:scale-95 font-semibold text-sm ${
          open ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}
        title="Chat with minimized document"
      >
        <MessageSquare className="w-4 h-4" />
        <span className="hidden sm:block">Ask Document</span>
      </button>

      {/* Chat Drawer */}
      {open && (
        <div
          id="chat-panel"
          className="fixed bottom-6 right-6 z-50 w-80 sm:w-96 bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-fade-in-up"
          style={{ maxHeight: '520px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4" />
              <span className="text-sm font-bold">Ask Minimized Document</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                id="chat-minimize-btn"
                onClick={() => setOpen(false)}
                className="p-1 rounded-lg hover:bg-white/20 transition-colors"
                title="Minimize chat"
              >
                <Minimize2 className="w-3.5 h-3.5" />
              </button>
              <button
                id="chat-close-btn"
                onClick={() => { setOpen(false); setMessages([]); }}
                className="p-1 rounded-lg hover:bg-white/20 transition-colors"
                title="Close chat"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Privacy Notice */}
          <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border-b border-emerald-200">
            <Shield className="w-3 h-3 text-emerald-600 shrink-0" />
            <p className="text-[10px] text-emerald-700 font-semibold">
              Chat uses minimized document only — no original PII visible to AI
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3" style={{ minHeight: '200px' }}>
            {messages.length === 0 && (
              <div className="text-center space-y-2 py-4">
                <Bot className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-[11px] text-slate-400 font-medium">
                  Ask questions about your minimized document
                </p>
                <div className="flex flex-col gap-1.5">
                  {['What is my total spend?', 'Which merchants appear?', 'What is the closing balance?'].map((q) => (
                    <button
                      key={q}
                      onClick={() => setInput(q)}
                      className="text-[11px] text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5 hover:bg-blue-100 transition-colors text-left font-medium"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {msg.role === 'user' ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                </div>
                <div
                  className={`max-w-[75%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-tr-sm'
                      : 'bg-slate-100 text-slate-800 rounded-tl-sm'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
                  <Bot className="w-3 h-3" />
                </div>
                <div className="px-3 py-2 rounded-xl bg-slate-100 rounded-tl-sm">
                  <Loader2 className="w-3 h-3 text-slate-500 animate-spin" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-3 py-3 border-t border-slate-200 flex gap-2">
            <input
              id="chat-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the document…"
              className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white text-slate-800 placeholder-slate-400"
            />
            <button
              id="chat-send-btn"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-all active:scale-95 disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
