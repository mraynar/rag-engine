// frontend/app/page.js
// Chat page — POST /chat, renders conversation bubbles, sources, loading & error states.
// Uses CSS Modules (chat.module.css) to avoid SSR hydration mismatches
// caused by injecting <style> strings in a 'use client' component.
'use client';

import { useState, useRef, useEffect } from 'react';
import s from './chat.module.css';
import {
  ChatIcon,
  AlertCircleIcon,
  XIcon,
  SendIcon,
  SpinnerIcon,
  SunIcon,
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ---- Thinking / loading indicator (3 animated dots) ----
function ThinkingIndicator() {
  return (
    <div className={`${s.bubbleRow} ${s.bubbleRowAi}`} aria-label="AI sedang memproses">
      <div className={`${s.bubble} ${s.bubbleAi} ${s.bubbleThinking}`}>
        <span className={s.dot} />
        <span className={s.dot} />
        <span className={s.dot} />
      </div>
    </div>
  );
}

// ---- Single source tag pill ----
function SourceTag({ label }) {
  return <span className={s.sourceTag}>{label}</span>;
}

// ---- One conversation turn ----
function MessageBubble({ role, content, sources }) {
  const isUser = role === 'user';
  return (
    <div className={`${s.bubbleRow} ${isUser ? s.bubbleRowUser : s.bubbleRowAi}`}>
      {!isUser && (
        <div className={s.bubbleAvatar} aria-hidden="true">
          {/* AI avatar — sun/spark icon */}
          <SunIcon size={16} />
        </div>
      )}
      <div className={s.bubbleContent}>
        <div className={`${s.bubble} ${isUser ? s.bubbleUser : s.bubbleAi}`}>
          {content}
        </div>
        {!isUser && sources && sources.length > 0 && (
          <div className={s.sourcesRow} aria-label="Sumber dokumen">
            <span className={s.sourcesLabel}>Sumber:</span>
            {sources.map((src, i) => (
              <SourceTag key={i} label={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Empty / welcome state ----
function EmptyState() {
  const suggestions = [
    'Apa itu PT TPS Pelindo?',
    'Apa layanan utama terminal petikemas ini?',
    'Bagaimana kapasitas throughput TPS?',
  ];

  return (
    <div className={s.emptyState}>
      <div className={s.emptyIcon} aria-hidden="true">
        <ChatIcon size={36} />
      </div>
      <h2 className={s.emptyTitle}>Tanya apa saja tentang dokumen TPS</h2>
      <p className={s.emptyDesc}>
        AI akan menjawab berdasarkan dokumen yang telah diindeks.
      </p>
      <div className={s.suggestions}>
        {suggestions.map((text, i) => (
          <button
            key={i}
            className={s.suggestionChip}
            onClick={() => {
              // Custom event picked up by the input listener below
              window.dispatchEvent(new CustomEvent('set-suggestion', { detail: text }));
            }}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---- Main Chat Page ----
export default function ChatPage() {
  const [messages, setMessages] = useState([]); // { role: 'user'|'ai', content, sources? }
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Listen for suggestion chip clicks (emitted from EmptyState)
  useEffect(() => {
    const handler = (e) => {
      setInput(e.detail);
      inputRef.current?.focus();
    };
    window.addEventListener('set-suggestion', handler);
    return () => window.removeEventListener('set-suggestion', handler);
  }, []);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    // Append user message immediately for responsiveness
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      setMessages(prev => [
        ...prev,
        { role: 'ai', content: data.answer, sources: data.sources || [] },
      ]);
    } catch (err) {
      setError(
        err.message ||
        'Gagal terhubung ke server. Pastikan backend berjalan di port 8000.'
      );
    } finally {
      setLoading(false);
      // Re-focus input after the response lands
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e) {
    // Enter = send, Shift+Enter = new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className={s.chatPage}>
      {/* ---- Message list ---- */}
      <div
        className={s.chatMessages}
        role="log"
        aria-live="polite"
        aria-label="Percakapan"
      >
        {isEmpty && <EmptyState />}

        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
          />
        ))}

        {loading && <ThinkingIndicator />}

        {/* Error banner */}
        {error && (
          <div className={s.errorBanner} role="alert">
            <AlertCircleIcon size={16} />
            <span>{error}</span>
            <button
              className={s.errorClose}
              onClick={() => setError(null)}
              aria-label="Tutup pesan error"
            >
              <XIcon size={14} />
            </button>
          </div>
        )}

        <div ref={bottomRef} aria-hidden="true" />
      </div>

      {/* ---- Input bar ---- */}
      <div className={s.inputBar}>
        <div className={s.inputWrapper}>
          <textarea
            ref={inputRef}
            id="chat-input"
            className={s.textarea}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ketik pertanyaan Anda…"
            disabled={loading}
            aria-label="Input pertanyaan"
            aria-disabled={loading}
          />
          <button
            id="chat-send-btn"
            className={`${s.sendBtn}${loading ? ` ${s.sendBtnLoading}` : ''}`}
            onClick={handleSend}
            disabled={loading || !input.trim()}
            aria-label="Kirim pertanyaan"
          >
            {loading
              ? <SpinnerIcon size={18} className={s.spinIcon} />
              : <SendIcon size={18} />
            }
          </button>
        </div>
        <p className={s.inputHint}>
          Enter untuk kirim &nbsp;·&nbsp; Shift+Enter untuk baris baru
        </p>
      </div>
    </div>
  );
}
