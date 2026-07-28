// frontend/app/page.js
// Chat page — sidebar conversation list + main chat panel.
// Active conversation tracked via URL param: /chat?id=conv_xxx
// Draft text preserved per-conversation in sessionStorage.
'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import s from './chat.module.css';
import {
  ChatIcon, AlertCircleIcon, XIcon, SendIcon, SpinnerIcon, SunIcon,
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─────────────────────────────────────────────────────
// Inline SVG icons for sidebar actions
// ─────────────────────────────────────────────────────

function PinIcon({ size = 14, filled = false }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
  );
}

function PencilIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  );
}

function TrashIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
    </svg>
  );
}

function PlusIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19"/>
      <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  );
}

function CheckIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}

// ─────────────────────────────────────────────────────
// Relative timestamp helper
// ─────────────────────────────────────────────────────

function relativeTime(isoStr) {
  if (!isoStr) return '';
  const ms = Date.now() - new Date(isoStr + 'Z').getTime();
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return 'Baru saja';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} menit lalu`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} jam lalu`;
  const day = Math.floor(hr / 24);
  return `${day} hari lalu`;
}

// ─────────────────────────────────────────────────────
// Draft text helpers (sessionStorage keyed by conv_id)
// ─────────────────────────────────────────────────────

function getDraft(convId) {
  try { return sessionStorage.getItem(`draft_${convId}`) || ''; } catch { return ''; }
}
function setDraft(convId, text) {
  try {
    if (text) sessionStorage.setItem(`draft_${convId}`, text);
    else sessionStorage.removeItem(`draft_${convId}`);
  } catch {}
}

// ─────────────────────────────────────────────────────
// Subcomponents
// ─────────────────────────────────────────────────────

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

function EmptyState({ onSuggestion }) {
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
      <p className={s.emptyDesc}>AI akan menjawab berdasarkan dokumen yang telah diindeks.</p>
      <div className={s.suggestions}>
        {suggestions.map((text, i) => (
          <button key={i} className={s.suggestionChip} onClick={() => onSuggestion(text)}>
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────
// Sidebar — conversation list
// ─────────────────────────────────────────────────────

function ConversationItem({ conv, isActive, onSelect, onRename, onPin, onDelete }) {
  const [editing, setEditing]   = useState(false);
  const [title, setTitle]       = useState(conv.title);
  const [showMenu, setShowMenu] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

  function commitRename() {
    setEditing(false);
    setShowMenu(false);
    if (title.trim() && title.trim() !== conv.title) {
      onRename(conv.id, title.trim());
    } else {
      setTitle(conv.title); // revert
    }
  }

  return (
    <div
      className={`${s.convItem} ${isActive ? s.convItemActive : ''}`}
      onClick={() => !editing && onSelect(conv.id)}
      onMouseEnter={() => setShowMenu(true)}
      onMouseLeave={() => { setShowMenu(false); }}
    >
      {conv.pinned && (
        <span className={s.convPin} title="Disematkan">
          <PinIcon size={11} filled />
        </span>
      )}

      {editing ? (
        <input
          ref={inputRef}
          className={s.convRenameInput}
          value={title}
          onChange={e => setTitle(e.target.value)}
          onBlur={commitRename}
          onKeyDown={e => {
            if (e.key === 'Enter') commitRename();
            if (e.key === 'Escape') { setEditing(false); setTitle(conv.title); }
          }}
          onClick={e => e.stopPropagation()}
        />
      ) : (
        <span className={s.convTitle}>{conv.title}</span>
      )}

      <span className={s.convTime}>{relativeTime(conv.updated_at)}</span>

      {(showMenu || isActive) && !editing && (
        <div className={s.convActions} onClick={e => e.stopPropagation()}>
          <button
            className={s.convActionBtn}
            title="Ganti nama"
            aria-label="Ganti nama percakapan"
            onClick={() => setEditing(true)}
          >
            <PencilIcon size={12} />
          </button>
          <button
            className={s.convActionBtn}
            title={conv.pinned ? 'Lepas sematkan' : 'Sematkan'}
            aria-label={conv.pinned ? 'Lepas sematkan' : 'Sematkan percakapan'}
            onClick={() => onPin(conv.id, !conv.pinned)}
          >
            <PinIcon size={12} filled={conv.pinned} />
          </button>
          <button
            className={`${s.convActionBtn} ${s.convActionDanger}`}
            title="Hapus"
            aria-label="Hapus percakapan"
            onClick={() => onDelete(conv.id)}
          >
            <TrashIcon size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────
// Main chat page — wrapped in Suspense for useSearchParams
// ─────────────────────────────────────────────────────

function ChatPageInner() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const convId       = searchParams.get('id');

  const [conversations, setConversations] = useState([]); // summaries
  const [messages, setMessages]           = useState([]);
  const [input, setInput]                 = useState('');
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState(null);
  const [loadingConvs, setLoadingConvs]   = useState(true);
  const [sidebarOpen, setSidebarOpen]     = useState(true);
  const [newConvBlocked, setNewConvBlocked] = useState(false); // for shake feedback

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // ---- Load conversation list ----
  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/conversations`);
      if (res.ok) setConversations(await res.json());
    } finally {
      setLoadingConvs(false);
    }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  // ---- Load messages when conv changes ----
  useEffect(() => {
    if (!convId) return;
    // Restore draft for this conversation
    setInput(getDraft(convId));
    // Fetch full messages
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

  // ---- On load with no ?id param: reuse existing empty conv, or create new ----
  // This effect runs once per mount (when loadingConvs transitions false→true).
  // IMPORTANT: do NOT create a new conversation if one already exists with 0 messages —
  // that would spam-create empties every time the user navigates away and back.
  useEffect(() => {
    if (loadingConvs) return;
    if (convId) return; // already have an id in URL, nothing to do

    // conversations state is updated before loadingConvs goes false, so we can
    // read it directly here (no stale closure issue).
    setConversations(prev => {
      const emptyConv = prev.find(c => c.message_count === 0);
      if (emptyConv) {
        // Reuse the existing empty conversation — don't create another one
        router.replace(`/?id=${emptyConv.id}`);
      } else if (prev.length === 0) {
        // No conversations at all — create the very first one
        createAndSelectConv(true);
      } else {
        // Conversations exist but all have messages — navigate to the most recent
        router.replace(`/?id=${prev[0].id}`);
      }
      return prev; // no state mutation, just side-effect
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingConvs]);

  // ---- Auto-scroll ----
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ---- Helpers ----
  async function createAndSelectConv(force = false) {
    // Guard: if the active conversation already has zero messages, don't create
    // another empty one — just give feedback and stay put.
    if (!force && convId && messages.length === 0) {
      setNewConvBlocked(true);
      setTimeout(() => setNewConvBlocked(false), 600);
      return;
    }
    const res = await fetch(`${API_URL}/conversations`, { method: 'POST' });
    if (!res.ok) return;
    const data = await res.json();
    router.replace(`/?id=${data.id}`);
    await loadConversations();
  }

  function selectConv(id) {
    // Save current draft before switching
    if (convId) setDraft(convId, input);
    router.push(`/?id=${id}`);
    setMessages([]);
    setError(null);
  }

  async function handleRename(id, newTitle) {
    await fetch(`${API_URL}/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    });
    await loadConversations();
  }

  async function handlePin(id, pinned) {
    await fetch(`${API_URL}/conversations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pinned }),
    });
    await loadConversations();
  }

  async function handleDelete(id) {
    await fetch(`${API_URL}/conversations/${id}`, { method: 'DELETE' });
    await loadConversations();
    if (id === convId) {
      // Navigate to first remaining conversation, or create new one
      const remaining = conversations.filter(c => c.id !== id);
      if (remaining.length > 0) {
        router.push(`/?id=${remaining[0].id}`);
      } else {
        await createAndSelectConv();
      }
    }
  }

  // ---- Send message ----
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
        body: JSON.stringify({ message: text, conversation_id: convId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources || [] }]);
      // Refresh sidebar so title updates after first message
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

  const isEmpty = messages.length === 0 && !loading;

  // Pinned and unpinned groups
  const pinnedConvs   = conversations.filter(c => c.pinned);
  const unpinnedConvs = conversations.filter(c => !c.pinned);

  return (
    <div className={s.chatShell}>
      {/* ── Sidebar ── */}
      <aside className={`${s.sidebar} ${sidebarOpen ? s.sidebarOpen : s.sidebarClosed}`}
        aria-label="Daftar percakapan">

        {/* Sidebar header */}
        <div className={s.sidebarHeader}>
          <span className={s.sidebarTitle}>Percakapan</span>
          <button
            className={`${s.newConvBtn}${newConvBlocked ? ` ${s.newConvBtnShake}` : ''}`}
            onClick={() => createAndSelectConv()}
            title={newConvBlocked ? 'Percakapan ini masih kosong — mulai mengetik dulu' : 'Percakapan baru'}
            aria-label="Percakapan baru"
            id="new-conv-btn"
          >
            <PlusIcon size={14} />
            Baru
          </button>
        </div>

        {/* Conversation list */}
        <div className={s.convList}>
          {loadingConvs && (
            <div className={s.convLoading}>
              <SpinnerIcon size={18} className={s.spinIcon} />
            </div>
          )}

          {!loadingConvs && conversations.length === 0 && (
            <p className={s.convEmpty}>Belum ada percakapan</p>
          )}

          {pinnedConvs.length > 0 && (
            <>
              <p className={s.convGroupLabel}>Disematkan</p>
              {pinnedConvs.map(c => (
                <ConversationItem
                  key={c.id}
                  conv={c}
                  isActive={c.id === convId}
                  onSelect={selectConv}
                  onRename={handleRename}
                  onPin={handlePin}
                  onDelete={handleDelete}
                />
              ))}
            </>
          )}

          {unpinnedConvs.length > 0 && (
            <>
              {pinnedConvs.length > 0 && <p className={s.convGroupLabel}>Lainnya</p>}
              {unpinnedConvs.map(c => (
                <ConversationItem
                  key={c.id}
                  conv={c}
                  isActive={c.id === convId}
                  onSelect={selectConv}
                  onRename={handleRename}
                  onPin={handlePin}
                  onDelete={handleDelete}
                />
              ))}
            </>
          )}
        </div>
      </aside>

      {/* ── Main chat panel ── */}
      <div className={s.chatMain}>
        {/* Message list */}
        <div className={s.chatMessages} role="log" aria-live="polite" aria-label="Percakapan">
          {isEmpty && <EmptyState onSuggestion={text => { setInput(text); inputRef.current?.focus(); }} />}

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

        {/* Input bar */}
        <div className={s.inputBar}>
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
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><SpinnerIcon size={24} /></div>}>
      <ChatPageInner />
    </Suspense>
  );
}
