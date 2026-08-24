'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import ReactMarkdown from 'react-markdown';
import { useCategory } from './CategoryContext';
import { useConversation } from './ConversationContext';
import s from './chat.module.css';
import {
  AlertCircleIcon, XIcon, SendIcon, SpinnerIcon,
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Inline SVG icons used only inside this file ────────────────────────────

function PlusIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function PencilIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function PinIcon({ size = 13, filled = false }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill={filled ? '#fff' : 'none'} />
    </svg>
  );
}

function TrashIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

function CheckIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

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

// ─── Draft text helpers (sessionStorage keyed by conv_id) ───────────────────

function getDraft(convId) {
  try { return sessionStorage.getItem(`draft_${convId}`) || ''; } catch { return ''; }
}
function setDraft(convId, text) {
  try {
    if (text) sessionStorage.setItem(`draft_${convId}`, text);
    else sessionStorage.removeItem(`draft_${convId}`);
  } catch {}
}

// ─── Helper: relative time ───────────────────────────────────────────────────

function relativeTime(isoStr) {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr + 'Z').getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)   return 'Baru saja';
  if (m < 60)  return `${m} mnt lalu`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h} jam lalu`;
  const d = Math.floor(h / 24);
  if (d === 1) return 'Kemarin';
  if (d < 7)   return `${d} hari lalu`;
  return new Date(isoStr + 'Z').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
}

// ─── Subcomponents ───────────────────────────────────────────────────────────

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
  
  let mainContent = content;
  let debugContent = '';

  if (!isUser && content && content.includes('\n---\n### Debug Information')) {
    const parts = content.split('\n---\n### Debug Information');
    mainContent = parts[0];
    debugContent = '### Debug Information' + parts[1];
  } else if (!isUser && content && content.includes('---') && content.includes('Debug Information')) {
    const parts = content.split('---');
    for (let idx = 0; idx < parts.length; idx++) {
      if (parts[idx].includes('Debug Information')) {
        mainContent = parts.slice(0, idx).join('---');
        debugContent = parts.slice(idx).join('---');
        if (!debugContent.startsWith('###') && debugContent.includes('Debug Information')) {
          debugContent = '### ' + debugContent.trim();
        }
        break;
      }
    }
  }

  return (
    <div className={`${s.bubbleRow} ${isUser ? s.bubbleRowUser : s.bubbleRowAi}`}>
      {!isUser && (
        <div className={s.bubbleAvatar} aria-hidden="true" style={{
          backgroundColor: '#fff',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <img
            src="/images/Logo Pelindo.png"
            alt="Pelindo"
            style={{ width: '85%', height: '85%', objectFit: 'contain' }}
          />
        </div>
      )}
      <div className={s.bubbleContent}>
        <div className={`${s.bubble} ${isUser ? s.bubbleUser : s.bubbleAi}`}>
          {isUser
            ? mainContent
            : (
              <div className={s.markdownContent}>
                <ReactMarkdown>{mainContent}</ReactMarkdown>
              </div>
            )
          }
        </div>
        {!isUser && debugContent && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            backgroundColor: '#f8fafc',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            fontSize: '0.8rem',
            color: 'var(--color-text-light)',
            width: '100%',
            maxWidth: '100%',
            overflowX: 'auto',
          }}>
            <div className={s.markdownContent}>
              <ReactMarkdown>{debugContent}</ReactMarkdown>
            </div>
          </div>
        )}
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

// ─── Sidebar single item ─────────────────────────────────────────────────────

function ConvItem({ conv, isActive, onSelect, onRename, onPin, onDelete }) {
  const [hovered, setHovered]   = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraftTitle]  = useState(conv.title);
  const [contextMenu, setContextMenu] = useState(null); // { x, y }
  const inputRef = useRef(null);

  useEffect(() => {
    if (renaming) { inputRef.current?.focus(); inputRef.current?.select(); }
  }, [renaming]);

  // Click outside to close context menu
  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener('click', closeMenu);
    window.addEventListener('contextmenu', closeMenu);
    return () => {
      window.removeEventListener('click', closeMenu);
      window.removeEventListener('contextmenu', closeMenu);
    };
  }, []);

  function commitRename() {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== conv.title) onRename(conv.id, trimmed);
    setRenaming(false);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter')  { e.preventDefault(); commitRename(); }
    if (e.key === 'Escape') { setDraftTitle(conv.title); setRenaming(false); }
  }

  const handleContextMenu = (e) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  return (
    <div
      className={`${s.convItem} ${isActive ? s.convItemActive : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => !renaming && onSelect(conv.id)}
      onContextMenu={handleContextMenu}
      role="button"
      aria-current={isActive ? 'true' : undefined}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && !renaming && onSelect(conv.id)}
    >
      {conv.pinned && (
        <span className={s.convPin} title="Disematkan">
          <PinIcon size={10} filled />
        </span>
      )}

      {renaming ? (
        <input
          ref={inputRef}
          className={s.convRenameInput}
          value={draft}
          onChange={e => setDraftTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitRename}
          onClick={e => e.stopPropagation()}
          maxLength={80}
          aria-label="Ganti nama percakapan"
        />
      ) : (
        <span className={s.convTitle} title={conv.title}>{conv.title}</span>
      )}

      <span className={s.convTime}>{relativeTime(conv.updated_at)}</span>

      {/* Action buttons — show on hover or active */}
      {(hovered || isActive) && !renaming && (
        <div className={s.convActions} onClick={e => e.stopPropagation()}>
          {/* Rename */}
          <button
            className={s.convActionBtn}
            title="Ganti Nama"
            onClick={() => { setDraftTitle(conv.title); setRenaming(true); }}
            aria-label="Ganti nama percakapan"
          >
            <PencilIcon size={12} />
          </button>

          {/* Pin / Unpin */}
          <button
            className={s.convActionBtn}
            title={conv.pinned ? 'Lepas sematan' : 'Sematkan'}
            onClick={() => onPin(conv.id, !conv.pinned)}
            aria-label={conv.pinned ? 'Lepas sematan' : 'Sematkan'}
          >
            <PinIcon size={12} filled={conv.pinned} />
          </button>

          {/* Delete */}
          <button
            className={`${s.convActionBtn} ${s.convActionDanger}`}
            title="Hapus"
            onClick={() => onDelete(conv.id)}
            aria-label="Hapus percakapan"
          >
            <TrashIcon size={12} />
          </button>
        </div>
      )}

      {/* Right-click custom context menu */}
      {contextMenu && (
        <div
          style={{
            position: 'fixed',
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
            backgroundColor: '#ffffff',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            boxShadow: 'var(--shadow-md)',
            padding: '4px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            minWidth: '140px',
          }}
          onClick={e => e.stopPropagation()}
          onContextMenu={e => e.preventDefault()}
        >
          <button
            onClick={() => {
              onPin(conv.id, !conv.pinned);
              setContextMenu(null);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              fontSize: '0.8rem',
              color: 'var(--color-text)',
              textAlign: 'left',
              width: '100%',
              borderRadius: '4px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '550',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--color-bg)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <PinIcon size={12} filled={conv.pinned} style={{ color: 'var(--color-accent)' }} />
            {conv.pinned ? 'Lepas Sematan' : 'Sematkan'}
          </button>
          <button
            onClick={() => {
              onDelete(conv.id);
              setContextMenu(null);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              fontSize: '0.8rem',
              color: 'var(--color-error)',
              textAlign: 'left',
              width: '100%',
              borderRadius: '4px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '550',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <TrashIcon size={12} style={{ color: 'var(--color-error)' }} />
            Hapus
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────

function Sidebar({ onNewChat }) {
  const {
    activeConvId, setActiveConvId,
    conversations, loadConversations,
    renameConversation, togglePin, deleteConversation
  } = useConversation();

  const [shake, setShake] = useState(false);

  const pinned   = conversations.filter(c => c.pinned);
  const unpinned = conversations.filter(c => !c.pinned);

  async function handleSelect(id) {
    setActiveConvId(id);
  }

  async function handleRename(id, newTitle) {
    await renameConversation(id, newTitle);
  }

  async function handlePin(id, pinned) {
    await togglePin(id, pinned);
  }

  async function handleDelete(id) {
    if (!window.confirm('Hapus percakapan ini?')) return;
    await deleteConversation(id);
  }

  return (
    <div className={s.sidebar} role="navigation" aria-label="Riwayat percakapan">
      {/* Header */}
      <div className={s.sidebarHeader}>
        <span className={s.sidebarTitle}>Riwayat</span>
        <button
          className={`${s.newConvBtn} ${shake ? s.newConvBtnShake : ''}`}
          onClick={async () => {
            const success = await onNewChat();
            if (!success) {
              setShake(true);
              setTimeout(() => setShake(false), 550);
            }
          }}
          aria-label="Mulai percakapan baru"
          title="Percakapan Baru"
        >
          <PlusIcon size={12} /> Baru
        </button>
      </div>

      {/* List */}
      <div className={s.convList} role="list">
        {pinned.length > 0 && (
          <>
            <div className={s.convGroupLabel} aria-hidden="true">Disematkan</div>
            {pinned.map(conv => (
              <ConvItem
                key={conv.id}
                conv={conv}
                isActive={conv.id === activeConvId}
                onSelect={handleSelect}
                onRename={handleRename}
                onPin={handlePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {unpinned.length > 0 && (
          <>
            {pinned.length > 0 && (
              <div className={s.convGroupLabel} aria-hidden="true">Terbaru</div>
            )}
            {unpinned.map(conv => (
              <ConvItem
                key={conv.id}
                conv={conv}
                isActive={conv.id === activeConvId}
                onSelect={handleSelect}
                onRename={handleRename}
                onPin={handlePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {conversations.length === 0 && (
          <div className={s.convEmpty}>Belum ada percakapan</div>
        )}
      </div>
    </div>
  );
}

// ─── Main Chat Interface (inner) ─────────────────────────────────────────────

function ChatInterfaceInner({ hideHeader = false, showSidebar = true }) {
  const { selectedCategory } = useCategory();
  const {
    activeConvId, setActiveConvId,
    conversations, loadingConvs,
    loadConversations,
    createConversation, getConversation, postChatMessage
  } = useConversation();

  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  // Track which convId's messages are currently loaded to avoid redundant fetches
  const loadedConvRef = useRef(null);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // ── Bootstrap: ensure there is always an active conversation ──────────────
  useEffect(() => {
    if (loadingConvs) return;

    // Already have an active conv — nothing to do
    if (activeConvId) return;

    // No active conv in localStorage → pick one or create
    if (conversations.length > 0) {
      // Prefer an empty conv (avoids polluting history); else use the latest
      const empty = conversations.find(c => c.message_count === 0);
      setActiveConvId(empty ? empty.id : conversations[0].id);
    } else {
      // No conversations at all → create one silently
      createConversation().then(data => {
        if (data) {
          setActiveConvId(data.id);
        }
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingConvs, activeConvId]);

  // ── Load messages when activeConvId changes ───────────────────────────────
  useEffect(() => {
    if (!activeConvId) return;
    if (loadedConvRef.current === activeConvId) return; // already loaded

    // Restore draft for this conversation
    setInput(getDraft(activeConvId));

    getConversation(activeConvId)
      .then(data => {
        if (!data) return;
        loadedConvRef.current = activeConvId;
        setMessages(data.messages.map(m => ({
          role:    m.role === 'assistant' ? 'ai' : 'user',
          content: m.content,
          sources: m.sources || [],
        })));
      })
      .catch(() => {});
  }, [activeConvId]);

  // Reset loadedConvRef when switching conversation so messages re-fetch
  const prevConvRef = useRef(null);
  useEffect(() => {
    if (prevConvRef.current !== activeConvId) {
      loadedConvRef.current = null;
      prevConvRef.current   = activeConvId;
      setMessages([]);
    }
  }, [activeConvId]);

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── New chat ──────────────────────────────────────────────────────────────
  async function handleNewChat() {
    if (messages.length === 0) {
      return false;
    }
    const data = await createConversation();
    if (!data) return false;
    setActiveConvId(data.id);
    return true;
  }

  // ── Send message ──────────────────────────────────────────────────────────
  async function handleSend() {
    const text = input.trim();
    if (!text || loading || !activeConvId) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    setDraft(activeConvId, '');
    setLoading(true);
    setError(null);

    try {
      const data = await postChatMessage(activeConvId, text, selectedCategory);
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources || [] }]);
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
    if (activeConvId) setDraft(activeConvId, v);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-bg)',
      fontFamily: "'Inter', sans-serif",
      overflow: 'hidden',
    }}>

      {/* Optional header (shown on standalone page, hidden when embedded in page.js) */}
      {!hideHeader && (
        <div style={{
          maxWidth: showSidebar ? '100%' : '1000px',
          width: '100%',
          margin: '0 auto',
          padding: '24px 24px 10px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '700', color: 'var(--color-navy)', margin: 0 }}>
              Chatbot TPS
            </h2>
            <button style={{
              background: 'none', border: 'none',
              color: 'var(--color-muted)', cursor: 'pointer',
              padding: '4px', display: 'flex', alignItems: 'center',
            }} title="Informasi Sistem">
              <InfoIcon size={16} />
            </button>
          </div>
          <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-muted)', paddingBottom: '4px' }}>
            Kategori Aktif: <strong style={{ color: 'var(--color-navy)' }}>{selectedCategory}</strong>
          </p>
        </div>
      )}

      {/* Shell: sidebar (optional) + chat main — centered as a unit */}
      <div style={{ flex: '1', display: 'flex', overflow: 'hidden', minHeight: 0 }}>
        {/* Centered wrapper — padding here gives equal spacing on all 4 sides */}
        <div style={{
          display: 'flex',
          flex: '1',
          maxWidth: showSidebar ? '1120px' : '900px',
          width: '100%',
          margin: '0 auto',
          padding: '4px 20px 16px 20px',
          overflow: 'hidden',
          minHeight: 0,
          boxSizing: 'border-box',
        }}>
          {/* ── Unified card: sidebar + chat in one rounded container ── */}
          <div style={{
            display: 'flex',
            flex: '1',
            borderRadius: '8px',
            overflow: 'hidden',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-sm)',
            minHeight: 0,
          }}>

            {/* ── Sidebar ── */}
            {showSidebar && <Sidebar onNewChat={handleNewChat} />}

            {/* ── Chat Main ── */}
            <div className={s.chatMain}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                flex: '1',
                overflow: 'hidden',
                minHeight: 0,
                backgroundColor: '#fff',
              }}>

              {/* Top bar — merges visually with sidebar corporate navy */}
              <div style={{
                backgroundColor: 'var(--color-navy)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#fff',
                padding: '12.5px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span style={{ fontWeight: '700', fontSize: '0.95rem', letterSpacing: '-0.01em' }}>Asisten TPS</span>
                  <span style={{ fontSize: '0.75rem', opacity: '0.85' }}>
                    Kategori: {selectedCategory} | Siap membantu Anda
                  </span>
                </div>
              </div>

              {/* Message log */}
              <div
                className={s.chatMessages}
                style={{ padding: '20px', background: '#F8FAFC', flex: '1', overflowY: 'auto' }}
                role="log" aria-live="polite" aria-label="Percakapan"
              >
                {messages.length === 0 && (
                  <div className={`${s.bubbleRow} ${s.bubbleRowAi}`}>
                    <div className={s.bubbleAvatar} aria-hidden="true" style={{
                      backgroundColor: '#fff',
                      border: '1px solid var(--color-border)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <img
                        src="/images/Logo Pelindo.png"
                        alt="Pelindo"
                        style={{ width: '85%', height: '85%', objectFit: 'contain' }}
                      />
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

              {/* Suggestion chips */}
              <div style={{
                padding: '8px 20px',
                borderTop: '1px solid var(--color-border)',
                background: '#fff',
                flexShrink: 0,
              }}>
                <p style={{ margin: '0 0 6px 0', fontSize: '0.75rem', fontWeight: '700', color: 'var(--color-text-light)' }}>
                  Pertanyaan yang sering diajukan:
                </p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {[
                    'Bagaimana cara mengecek status kontainer?',
                    'Berapa biaya layanan penanganan kontainer?',
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); inputRef.current?.focus(); }}
                      style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                        padding: '6px 12px',
                        borderRadius: '20px',
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        color: 'var(--color-text-light)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input area */}
              <div style={{
                padding: '10px 20px',
                borderTop: '1px solid var(--color-border)',
                background: '#fff',
                flexShrink: 0,
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
                    {loading ? <SpinnerIcon size={18} className={s.spinIcon} /> : <SendIcon size={18} />}
                  </button>
                </div>
                <p className={s.inputHint}>Enter untuk kirim&nbsp;·&nbsp;Shift+Enter untuk baris baru</p>
              </div>

              </div>
            </div>
            {/* end unified card */}
          </div>

        </div>{/* end centered maxWidth wrapper */}
      </div>
    </div>
  );
}

// ─── Public export ────────────────────────────────────────────────────────────

export default function ChatInterface({ hideHeader = false, showSidebar = true }) {
  return (
    <Suspense fallback={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <SpinnerIcon size={24} />
      </div>
    }>
      <ChatInterfaceInner hideHeader={hideHeader} showSidebar={showSidebar} />
    </Suspense>
  );
}
