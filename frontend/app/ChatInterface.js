'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { useCategory } from './CategoryContext';
import s from './chat.module.css';
import {
  AlertCircleIcon, XIcon, SendIcon, SpinnerIcon, SunIcon,
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ---- Inline SVG Icons ----
function InfoIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

// ---- Draft text helpers (sessionStorage keyed by conv_id) ----
function getDraft(convId) {
  try { return sessionStorage.getItem(`draft_${convId}`) || ''; } catch { return ''; }
}
function setDraft(convId, text) {
  try {
    if (text) sessionStorage.setItem(`draft_${convId}`, text);
    else sessionStorage.removeItem(`draft_${convId}`);
  } catch {}
}

// ---- Subcomponents ----
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

function SourceTag({ label }) {
  return <span className={s.sourceTag}>{label}</span>;
}

function MessageBubble({ role, content, sources }) {
  const isUser = role === 'user';
  return (
    <div className={`${s.bubbleRow} ${isUser ? s.bubbleRowUser : s.bubbleRowAi}`}>
      {!isUser && (
        <div className={s.bubbleAvatar} aria-hidden="true">
          <SunIcon size={16} />
        </div>
      )}
      <div className={s.bubbleContent}>
        <div className={`${s.bubble} ${isUser ? s.bubbleUser : s.bubbleAi}`}>
          {isUser
            ? content
            : (
              <div className={s.markdownContent}>
                <ReactMarkdown>{content}</ReactMarkdown>
              </div>
            )
          }
        </div>
        {!isUser && sources && sources.length > 0 && (
          <div className={s.sourcesRow} aria-label="Sumber dokumen">
            <span className={s.sourcesLabel}>Sumber:</span>
            {Array.from(new Set(sources)).map((src, i) => <SourceTag key={i} label={src} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatInterfaceInner({ hideHeader = false }) {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const convId       = searchParams.get('id');

  const { selectedCategory } = useCategory();

  const [conversations, setConversations] = useState([]);
  const [messages, setMessages]           = useState([]);
  const [input, setInput]                 = useState('');
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState(null);
  const [loadingConvs, setLoadingConvs]   = useState(true);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // Load conversations
  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/conversations`);
      if (res.ok) setConversations(await res.json());
    } finally {
      setLoadingConvs(false);
    }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  // Load conversation details
  useEffect(() => {
    if (!convId) return;
    setInput(getDraft(convId));
    fetch(`${API_URL}/conversations/${convId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          setMessages(data.messages.map(m => ({
            role:    m.role === 'assistant' ? 'ai' : 'user',
            content: m.content,
            sources: m.sources || [],
          })));
        }
      });
  }, [convId]);

  // Handle empty state redirect (keeps 1 active conversation in the background)
  useEffect(() => {
    if (loadingConvs) return;
    if (convId) return;

    setConversations(prev => {
      const emptyConv = prev.find(c => c.message_count === 0);
      if (emptyConv) {
        router.replace(`/?id=${emptyConv.id}`);
      } else if (prev.length === 0) {
        createAndSelectConv(true);
      } else {
        router.replace(`/?id=${prev[0].id}`);
      }
      return prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingConvs]);

  // Scroll bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function createAndSelectConv(force = false) {
    const res = await fetch(`${API_URL}/conversations`, { method: 'POST' });
    if (!res.ok) return;
    const data = await res.json();
    router.replace(`/?id=${data.id}`);
    await loadConversations();
  }

  // Send message
  async function handleSend() {
    const text = input.trim();
    if (!text || loading || !convId) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setDraft(convId, '');
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: convId,
          category: selectedCategory === "Semua Data" ? null : selectedCategory
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources || [] }]);
      await loadConversations();
    } catch (err) {
      setError(err.message || 'Gagal terhubung ke server.');
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleInputChange(e) {
    const v = e.target.value;
    setInput(v);
    if (convId) setDraft(convId, v);
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-bg)',
      fontFamily: "'Inter', sans-serif",
      overflow: 'hidden'
    }}>
      
      {/* ── Main Layout Header (Centered Column match) ── */}
      {!hideHeader && (
        <div style={{
          maxWidth: '1000px',
          width: '100%',
          margin: '0 auto',
          padding: '24px 24px 10px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          flexShrink: 0
        }}>
          
          {/* Title + Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{
              fontSize: '1.4rem',
              fontWeight: '700',
              color: 'var(--color-navy)',
              margin: 0
            }}>
              Layanan Pelanggan TPS
            </h2>
            <button style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-muted)',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center'
            }} title="Informasi Sistem">
              <InfoIcon size={16} />
            </button>
          </div>

          {/* Selected Category Context Subtitle */}
          <p style={{
            margin: 0,
            fontSize: '0.75rem',
            color: 'var(--color-muted)',
            paddingBottom: '4px'
          }}>
            Kategori Aktif: <strong style={{ color: 'var(--color-navy)' }}>{selectedCategory}</strong>
          </p>
        </div>
      )}

      {/* ── Active Tab Workspace Content (Centered Layout Flow) ── */}
      <div style={{ flex: '1', display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative', minHeight: 0 }}>
        
        {/* ──── Chat Workspace (Single Centered Column, No Sidebar) ──── */}
        <div style={{
          maxWidth: '1000px',
          width: '100%',
          margin: '0 auto',
          padding: '10px 24px 24px 24px',
          display: 'flex',
          flexDirection: 'column',
          flex: '1',
          overflow: 'hidden',
          minHeight: 0
        }}>
          {/* The Unified Chat Box Card */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#fff',
            border: '1px solid var(--color-border)',
            borderRadius: '8px',
            boxShadow: 'var(--shadow-sm)',
            overflow: 'hidden',
            flex: '1',
            minHeight: 0
          }}>
            
            {/* Asisten TPS Header Bar */}
            <div style={{
              backgroundColor: 'var(--color-navy)',
              color: '#fff',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontWeight: '700', fontSize: '0.95rem', letterSpacing: '-0.01em' }}>Asisten TPS</span>
                <span style={{ fontSize: '0.75rem', opacity: '0.85' }}>
                  Kategori: {selectedCategory} | Siap membantu Anda
                </span>
              </div>
            </div>

            {/* Message Log */}
            <div className={s.chatMessages} style={{ padding: '20px', background: '#F8FAFC', flex: '1', overflowY: 'auto' }} role="log" aria-live="polite" aria-label="Percakapan">
              {/* Default Welcome Message when conversation is empty */}
              {messages.length === 0 && (
                <div className={`${s.bubbleRow} ${s.bubbleRowAi}`}>
                  <div className={s.bubbleAvatar} aria-hidden="true">
                    <SunIcon size={16} />
                  </div>
                  <div className={s.bubbleContent}>
                    <div className={`${s.bubble} ${s.bubbleAi}`}>
                      Selamat datang di Chatbot Terminal Petikemas Surabaya. Bagaimana saya bisa membantu Anda hari ini?
                    </div>
                    <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)', marginLeft: '12px', marginTop: '4px', display: 'inline-block' }}>
                      {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <MessageBubble key={i} role={msg.role} content={msg.content} sources={msg.sources} />
              ))}

              {loading && <ThinkingIndicator />}

              {error && (
                <div className={s.errorBanner} role="alert">
                  <AlertCircleIcon size={16} />
                  <span>{error}</span>
                  <button className={s.errorClose} onClick={() => setError(null)} aria-label="Tutup pesan error">
                    <XIcon size={14} />
                  </button>
                </div>
              )}

              <div ref={bottomRef} aria-hidden="true" />
            </div>

            {/* Suggestion Chips Box */}
            <div style={{
              padding: '12px 20px',
              borderTop: '1px solid var(--color-border)',
              background: '#fff',
              flexShrink: 0
            }}>
              <p style={{ margin: '0 0 8px 0', fontSize: '0.75rem', fontWeight: '700', color: 'var(--color-text-light)' }}>
                Pertanyaan yang sering diajukan:
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => { setInput('Bagaimana cara mengecek status kontainer?'); inputRef.current?.focus(); }}
                  style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    color: 'var(--color-text-light)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  Bagaimana cara mengecek status kontainer?
                </button>
                <button
                  onClick={() => { setInput('Berapa biaya layanan penanganan kontainer?'); inputRef.current?.focus(); }}
                  style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    color: 'var(--color-text-light)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  Berapa biaya layanan penanganan kontainer?
                </button>
              </div>
            </div>

            {/* Input Area */}
            <div style={{
              padding: '16px 20px',
              borderTop: '1px solid var(--color-border)',
              background: '#fff',
              flexShrink: 0
            }}>
              <div className={s.inputWrapper}>
                <textarea
                  ref={inputRef}
                  id="chat-input"
                  className={s.textarea}
                  rows={1}
                  value={input}
                  onChange={handleInputChange}
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
              <p className={s.inputHint}>Enter untuk kirim&nbsp;·&nbsp; Shift+Enter untuk baris baru</p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatInterface({ hideHeader = false }) {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><SpinnerIcon size={24} /></div>}>
      <ChatInterfaceInner hideHeader={hideHeader} />
    </Suspense>
  );
}
