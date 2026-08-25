'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import ReactMarkdown from 'react-markdown';
import { useCategory } from './CategoryContext';
import { useConversation } from './ConversationContext';
import s from './chat.module.css';
import {
  AlertCircleIcon, XIcon, SendIcon, SpinnerIcon,
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ─── Icons ───────────────────────────────────────────────────────────────────

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

function SidebarToggleIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  );
}

// ─── Draft helpers ────────────────────────────────────────────────────────────

function getDraft(convId) {
  try { return sessionStorage.getItem(`draft_${convId}`) || ''; } catch { return ''; }
}
function setDraft(convId, text) {
  try {
    if (text) sessionStorage.setItem(`draft_${convId}`, text);
    else sessionStorage.removeItem(`draft_${convId}`);
  } catch {}
}

// ─── Relative time ────────────────────────────────────────────────────────────

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

// ─── Thinking indicator ───────────────────────────────────────────────────────

function ThinkingIndicator() {
  return (
    <div className={s.thinkingRow} aria-label="AI sedang memproses">
      <div className={`${s.avatar} ${s.avatarAi}`}>
        <img
          src="/images/Logo Pelindo.png"
          alt="TPS"
          style={{ width: '82%', height: '82%', objectFit: 'contain' }}
        />
      </div>
      <div className={s.thinkingDots}>
        <span className={s.dot} />
        <span className={s.dot} />
        <span className={s.dot} />
      </div>
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ role, content, sources }) {
  const isUser = role === 'user';

  // Split debug info from main content
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
        if (!debugContent.startsWith('###')) debugContent = '### ' + debugContent.trim();
        break;
      }
    }
  }

  if (isUser) {
    return (
      <div className={s.msgRow}>
        <div className={s.msgRowUserInner}>
          <div className={`${s.avatar} ${s.avatarUser}`} aria-hidden="true">
            U
          </div>
          <div className={s.userBubble}>{mainContent}</div>
        </div>
      </div>
    );
  }

  // AI message — Claude/ChatGPT style: no bubble, direct text
  return (
    <div className={s.msgRow}>
      <div className={s.msgRowAiInner}>
        <div className={`${s.avatar} ${s.avatarAi}`} aria-hidden="true">
          <img
            src="/images/Logo Pelindo.png"
            alt="TPS"
            style={{ width: '82%', height: '82%', objectFit: 'contain' }}
          />
        </div>
        <div className={s.aiContent}>
          <div className={s.aiSender}>Asisten TPS</div>
          <div className={s.markdownContent}>
            <ReactMarkdown>{mainContent}</ReactMarkdown>
          </div>

          {debugContent && (
            <div style={{
              marginTop: '12px',
              padding: '12px 14px',
              background: 'var(--color-bg)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--r-md)',
              fontSize: '0.8rem',
              color: 'var(--color-text-muted)',
              overflowX: 'auto',
            }}>
              <div className={s.markdownContent}>
                <ReactMarkdown>{debugContent}</ReactMarkdown>
              </div>
            </div>
          )}

          {sources && sources.length > 0 && (
            <div className={s.sourcesRow} aria-label="Sumber dokumen">
              <span className={s.sourcesLabel}>Sumber:</span>
              {Array.from(new Set(sources)).map((src, i) => (
                <span key={i} className={s.sourceTag}>{src}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar conv item ────────────────────────────────────────────────────────

function ConvItem({ conv, isActive, onSelect, onRename, onPin, onDelete }) {
  const [hovered, setHovered]   = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraftTitle]  = useState(conv.title);
  const [contextMenu, setContextMenu] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (renaming) { inputRef.current?.focus(); inputRef.current?.select(); }
  }, [renaming]);

  useEffect(() => {
    const close = () => setContextMenu(null);
    window.addEventListener('click', close);
    window.addEventListener('contextmenu', close);
    return () => { window.removeEventListener('click', close); window.removeEventListener('contextmenu', close); };
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

      {(hovered || isActive) && !renaming && (
        <div className={s.convActions} onClick={e => e.stopPropagation()}>
          <button
            className={s.convActionBtn}
            title="Ganti Nama"
            onClick={() => { setDraftTitle(conv.title); setRenaming(true); }}
            aria-label="Ganti nama"
          >
            <PencilIcon size={12} />
          </button>
          <button
            className={s.convActionBtn}
            title={conv.pinned ? 'Lepas sematan' : 'Sematkan'}
            onClick={() => onPin(conv.id, !conv.pinned)}
            aria-label={conv.pinned ? 'Lepas sematan' : 'Sematkan'}
          >
            <PinIcon size={12} filled={conv.pinned} />
          </button>
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

      {contextMenu && (
        <div
          style={{
            position: 'fixed',
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
            background: '#fff',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--r-md)',
            boxShadow: 'var(--shadow-lg)',
            padding: '4px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            minWidth: '148px',
          }}
          onClick={e => e.stopPropagation()}
          onContextMenu={e => e.preventDefault()}
        >
          {[
            {
              label: conv.pinned ? 'Lepas Sematan' : 'Sematkan',
              icon: <PinIcon size={12} filled={conv.pinned} />,
              onClick: () => { onPin(conv.id, !conv.pinned); setContextMenu(null); },
              danger: false,
            },
            {
              label: 'Hapus',
              icon: <TrashIcon size={12} />,
              onClick: () => { onDelete(conv.id); setContextMenu(null); },
              danger: true,
            },
          ].map(item => (
            <button
              key={item.label}
              onClick={item.onClick}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '8px 12px', fontSize: '0.8125rem',
                color: item.danger ? 'var(--color-error)' : 'var(--color-text)',
                textAlign: 'left', width: '100%',
                borderRadius: 'var(--r-sm)', background: 'none',
                border: 'none', cursor: 'pointer', fontWeight: '500',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = item.danger ? 'rgba(239,68,68,0.08)' : 'var(--color-bg)'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              {item.icon}{item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ onNewChat }) {
  const {
    activeConvId, setActiveConvId,
    conversations,
    renameConversation, togglePin, deleteConversation,
  } = useConversation();

  const [shake, setShake] = useState(false);

  const pinned   = conversations.filter(c => c.pinned);
  const unpinned = conversations.filter(c => !c.pinned);

  async function handleDelete(id) {
    if (!window.confirm('Hapus percakapan ini?')) return;
    await deleteConversation(id);
  }

  return (
    <nav className={s.sidebar} aria-label="Riwayat percakapan">
      <div className={s.sidebarHeader}>
        <span className={s.sidebarTitle}>Riwayat</span>
        <button
          className={`${s.newConvBtn} ${shake ? s.newConvBtnShake : ''}`}
          onClick={async () => {
            const ok = await onNewChat();
            if (!ok) { setShake(true); setTimeout(() => setShake(false), 600); }
          }}
          aria-label="Percakapan baru"
        >
          <PlusIcon size={11} /> Baru
        </button>
      </div>

      <div className={s.convList} role="list">
        {pinned.length > 0 && (
          <>
            <div className={s.convGroupLabel} aria-hidden="true">Disematkan</div>
            {pinned.map(conv => (
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId}
                onSelect={setActiveConvId}
                onRename={renameConversation}
                onPin={togglePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {unpinned.length > 0 && (
          <>
            {pinned.length > 0 && <div className={s.convGroupLabel} aria-hidden="true">Terbaru</div>}
            {unpinned.map(conv => (
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId}
                onSelect={setActiveConvId}
                onRename={renameConversation}
                onPin={togglePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {conversations.length === 0 && (
          <div className={s.convEmpty}>Mulai percakapan baru untuk melihat riwayat di sini.</div>
        )}
      </div>
    </nav>
  );
}

// ─── Main Chat ────────────────────────────────────────────────────────────────

function ChatInterfaceInner({ hideHeader = false, showSidebar = true }) {
  const { selectedCategory } = useCategory();
  const {
    activeConvId, setActiveConvId,
    conversations, loadingConvs,
    createConversation, getConversation, postChatMessage,
    renameConversation, togglePin,
  } = useConversation();

  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const loadedConvRef = useRef(null);
  const bottomRef     = useRef(null);
  const inputRef      = useRef(null);

  // Bootstrap: ensure active conversation
  useEffect(() => {
    if (loadingConvs || activeConvId) return;
    if (conversations.length > 0) {
      const empty = conversations.find(c => c.message_count === 0);
      setActiveConvId(empty ? empty.id : conversations[0].id);
    } else {
      createConversation().then(data => { if (data) setActiveConvId(data.id); });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingConvs, activeConvId]);

  // Load messages when conv changes
  useEffect(() => {
    if (!activeConvId) return;
    if (loadedConvRef.current === activeConvId) return;
    setInput(getDraft(activeConvId));
    getConversation(activeConvId)
      .then(data => {
        if (!data) return;
        loadedConvRef.current = activeConvId;
        setMessages(data.messages.map(m => ({
          role: m.role === 'assistant' ? 'ai' : 'user',
          content: m.content,
          sources: m.sources || [],
        })));
      }).catch(() => {});
  }, [activeConvId]);

  const prevConvRef = useRef(null);
  useEffect(() => {
    if (prevConvRef.current !== activeConvId) {
      loadedConvRef.current = null;
      prevConvRef.current = activeConvId;
      setMessages([]);
    }
  }, [activeConvId]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleNewChat() {
    if (messages.length === 0) return false;
    const data = await createConversation();
    if (!data) return false;
    setActiveConvId(data.id);
    return true;
  }

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

  const SUGGESTIONS = [
    'Bagaimana cara mengecek status kontainer?',
    'Berapa biaya layanan penanganan kontainer?',
  ];

  return (
    <div className={s.chatShell}>
      {/* ── Sidebar ── */}
      {showSidebar && (
        <div className={`${s.sidebar} ${sidebarOpen ? s.sidebarOpen : s.sidebarClosed}`}>
          <Sidebar onNewChat={handleNewChat} />
        </div>
      )}

      {/* ── Chat main ── */}
      <div className={s.chatMain}>

        {/* Inner top bar */}
        <div className={s.chatInnerHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {showSidebar && (
              <button
                className={s.sidebarToggleBtn}
                onClick={() => setSidebarOpen(o => !o)}
                aria-label={sidebarOpen ? 'Sembunyikan sidebar' : 'Tampilkan sidebar'}
                title={sidebarOpen ? 'Sembunyikan riwayat' : 'Tampilkan riwayat'}
              >
                <SidebarToggleIcon size={17} />
              </button>
            )}
            <span className={s.chatInnerTitle}>Asisten TPS</span>
          </div>
          <div className={s.chatInnerSub}>
            Kategori:&nbsp;
            <span className={s.chatInnerSubBadge}>{selectedCategory}</span>
          </div>
        </div>

        {/* Message list */}
        <div
          className={s.chatMessages}
          role="log"
          aria-live="polite"
          aria-label="Percakapan"
        >
          {messages.length === 0 && !loading && (
            <div className={s.emptyState}>
              <div className={s.emptyIcon}>
                <img
                  src="/images/Logo Pelindo.png"
                  alt="TPS"
                  style={{ width: '60%', height: '60%', objectFit: 'contain' }}
                />
              </div>
              <p className={s.emptyTitle}>Selamat datang di Asisten TPS</p>
              <p className={s.emptyDesc}>
                Tanyakan informasi seputar layanan Terminal Petikemas Surabaya.
                Saya siap membantu Anda.
              </p>
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
              <button className={s.errorClose} onClick={() => setError(null)} aria-label="Tutup">
                <XIcon size={14} />
              </button>
            </div>
          )}

          <div ref={bottomRef} aria-hidden="true" />
        </div>

        {/* Suggestions — only shown when no messages */}
        {messages.length === 0 && !loading && (
          <div className={s.suggestionsWrap}>
            <p className={s.suggestionsLabel}>Pertanyaan umum</p>
            <div className={s.suggestions}>
              {SUGGESTIONS.map(q => (
                <button
                  key={q}
                  className={s.suggestionChip}
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input area */}
        <div className={s.inputArea}>
          <div className={s.inputBarWrap}>
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
              />
              <button
                id="chat-send-btn"
                className={`${s.sendBtn}${loading ? ` ${s.sendBtnLoading}` : ''}`}
                onClick={handleSend}
                disabled={loading || !input.trim()}
                aria-label="Kirim"
              >
                {loading ? <SpinnerIcon size={16} className={s.spinIcon} /> : <SendIcon size={16} />}
              </button>
            </div>
            <p className={s.inputHint}>Enter untuk kirim · Shift+Enter untuk baris baru</p>
          </div>
        </div>

      </div>
    </div>
  );
}

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
