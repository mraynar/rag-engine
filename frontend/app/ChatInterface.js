'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import ReactMarkdown from 'react-markdown';
import { useCategory } from './CategoryContext';
import { useConversation } from './ConversationContext';
import { useAuth } from './AuthContext';
import CategorySelector from './CategorySelector';
import ConfigManager from './ConfigManager';
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

function Sidebar({ onNewChat, activeView, setActiveView, setSidebarOpen }) {
  const {
    activeConvId, setActiveConvId,
    conversations,
    renameConversation, togglePin, deleteConversation,
  } = useConversation();

  const { user, loading: authLoading, logout } = useAuth();
  const { setIsAuthModalOpen } = useCategory();

  const [shake, setShake] = useState(false);

  const pinned   = conversations.filter(c => c.pinned);
  const unpinned = conversations.filter(c => !c.pinned);

  async function handleDelete(id) {
    if (!window.confirm('Hapus percakapan ini?')) return;
    await deleteConversation(id);
  }

  return (
    <nav className={s.sidebar} aria-label="Riwayat percakapan">
      {/* Header with rounded White Card for TPS Logo and Close button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 14px 12px',
        borderBottom: '1px solid var(--sidebar-border)',
        flexShrink: 0
      }}>
        {/* White Card Container for TPS Logo */}
        <div style={{
          backgroundColor: '#FFFFFF',
          padding: '6px 12px',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-sm)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
          width: '120px',
          height: '36px'
        }}>
          <img
            src="/images/Logo_TPS.png"
            alt="Logo TPS"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        </div>

        {/* Sidebar Close Button */}
        <button
          onClick={() => setSidebarOpen(false)}
          title="Tutup riwayat"
          style={{
            color: 'rgba(255, 255, 255, 0.85)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: 'var(--r-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
          onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
        >
          <SidebarToggleIcon size={18} />
        </button>
      </div>

      {/* New Chat Button Row */}
      <div style={{ padding: '12px 14px 4px 14px', flexShrink: 0 }}>
        <button
          className={`${s.newConvBtn} ${shake ? s.newConvBtnShake : ''}`}
          onClick={async () => {
            setActiveView('chat');
            const ok = await onNewChat();
            if (!ok) { setShake(true); setTimeout(() => setShake(false), 600); }
          }}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 14px',
            borderRadius: 'var(--r-md)',
            background: 'rgba(255, 255, 255, 0.12)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            color: '#fff',
            fontWeight: '600',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.22)'}
          onMouseLeave={e => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.12)'}
        >
          <PlusIcon size={14} /> Baru
        </button>
      </div>

      {/* Conversations List (Riwayat) */}
      <div className={s.convList} role="list">
        {pinned.length > 0 && (
          <>
            <div className={s.convGroupLabel} aria-hidden="true">Disematkan</div>
            {pinned.map(conv => (
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId && activeView === 'chat'}
                onSelect={(id) => { setActiveView('chat'); setActiveConvId(id); }}
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
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId && activeView === 'chat'}
                onSelect={(id) => { setActiveView('chat'); setActiveConvId(id); }}
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

      {/* Sidebar Footer with Config & Login */}
      <div style={{
        borderTop: '1px solid var(--sidebar-border)',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        background: 'rgba(0, 0, 0, 0.08)',
        flexShrink: 0
      }}>
        {/* Configuration Button */}
        <button
          onClick={() => setActiveView('config')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            width: '100%',
            padding: '8px 10px',
            borderRadius: 'var(--r-sm)',
            color: '#fff',
            fontSize: '0.85rem',
            fontWeight: activeView === 'config' ? '600' : '500',
            background: activeView === 'config' ? 'rgba(255, 255, 255, 0.22)' : 'transparent',
            border: activeView === 'config' ? '1px solid rgba(255, 255, 255, 0.35)' : '1px solid transparent',
            cursor: 'pointer',
            textAlign: 'left',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={e => { if (activeView !== 'config') e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.12)'; }}
          onMouseLeave={e => { if (activeView !== 'config') e.currentTarget.style.backgroundColor = 'transparent'; }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>Konfigurasi</span>
        </button>

        {/* Auth status block */}
        {authLoading ? (
          <div style={{ height: '36px', background: 'rgba(255,255,255,0.08)', borderRadius: 'var(--r-sm)', animation: 'pulse 1.5s infinite' }} />
        ) : user ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 10px',
            borderRadius: 'var(--r-sm)',
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            gap: '8px',
            width: '100%',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                background: '#fff', color: 'var(--color-brand)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: '700', fontSize: '0.8rem', flexShrink: 0
              }}>
                {(user.user_metadata?.display_name || user.email)[0].toUpperCase()}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <span style={{ fontSize: '0.8rem', color: '#fff', fontWeight: '600', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '130px' }}>
                  {user.user_metadata?.display_name || user.email.split('@')[0]}
                </span>
                <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '130px' }}>
                  {user.email}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              title="Keluar dari akun"
              style={{
                padding: '6px', borderRadius: 'var(--r-sm)',
                color: 'rgba(255, 255, 255, 0.85)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.3)';
                e.currentTarget.style.color = '#fff';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'rgba(255, 255, 255, 0.85)';
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsAuthModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              width: '100%',
              padding: '10px',
              borderRadius: 'var(--r-sm)',
              background: '#ffffff',
              color: 'var(--color-brand)',
              fontWeight: '600',
              fontSize: '0.8rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: 'var(--shadow-sm)',
              border: '1px solid transparent'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = '#EBF4FF';
              e.currentTarget.style.color = 'var(--color-brand-dark)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = '#ffffff';
              e.currentTarget.style.color = 'var(--color-brand)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
              <polyline points="10 17 15 12 10 7" />
              <line x1="15" y1="12" x2="3" y2="12" />
            </svg>
            <span>Masuk / Daftar</span>
          </button>
        )}
      </div>
    </nav>
  );
}

// ─── Main Chat Interface Inner ───────────────────────────────────────────────

function ChatInterfaceInner({ hideHeader = false, showSidebar = true }) {
  const { selectedCategory } = useCategory();
  const {
    activeConvId, setActiveConvId,
    conversations, loadingConvs,
    createConversation, getConversation, postChatMessage,
  } = useConversation();

  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeView, setActiveView]   = useState('chat'); // 'chat' or 'config'
  const [isListening, setIsListening] = useState(false);

  const loadedConvRef = useRef(null);
  const bottomRef     = useRef(null);
  const inputRef      = useRef(null);
  const recognitionRef = useRef(null);

  // Bootstrap active conversation
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
    if (activeView === 'chat') {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, activeView]);

  // Auto-resize textarea height as content changes
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 240)}px`;
    }
  }, [input]);

  // Speech Recognition API
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'id-ID';

      rec.onstart = () => setIsListening(true);
      rec.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript;
        setInput(prev => {
          const newText = prev ? prev.trim() + ' ' + transcript : transcript;
          if (activeConvId) setDraft(activeConvId, newText);
          return newText;
        });
      };
      rec.onerror = () => setIsListening(false);
      rec.onend = () => setIsListening(false);

      recognitionRef.current = rec;
    }
  }, [activeConvId]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Browser Anda tidak mendukung input suara (Speech Recognition).');
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

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

  return (
    <div className={s.chatShell}>
      {/* ── Sidebar ── */}
      {showSidebar && (
        <div className={`${s.sidebar} ${sidebarOpen ? s.sidebarOpen : s.sidebarClosed}`}>
          <Sidebar
            onNewChat={handleNewChat}
            activeView={activeView}
            setActiveView={setActiveView}
            setSidebarOpen={setSidebarOpen}
          />
        </div>
      )}

      {/* ── Chat main panel ── */}
      <div className={s.chatMain}>

        {/* Top Navbar Header — industry standard */}
        <div className={s.chatInnerHeader} style={{ height: '56px', padding: '0 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Sidebar toggle button (visible when sidebar is closed) */}
            {showSidebar && !sidebarOpen && (
              <button
                className={s.sidebarToggleBtn}
                onClick={() => setSidebarOpen(true)}
                title="Tampilkan riwayat"
                aria-label="Buka sidebar"
              >
                <SidebarToggleIcon size={17} />
              </button>
            )}

            {/* Shield Logo Pelindo (visible only when sidebar is closed) */}
            {showSidebar && !sidebarOpen && (
              <div style={{ height: '32px', display: 'flex', alignItems: 'center', marginRight: '4px' }}>
                <img
                  src="/images/Logo Pelindo.png"
                  alt="Logo Pelindo"
                  style={{ height: '100%', objectFit: 'contain' }}
                />
              </div>
            )}

            <span className={s.chatInnerTitle} style={{ fontSize: '0.9rem', fontWeight: '700' }}>
              Asisten TPS
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Powered by Gemini Badge */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              fontSize: '0.72rem', fontWeight: '600',
              color: '#1c6bbf',
              background: 'var(--color-brand-light)',
              border: '1px solid rgba(43,127,214,0.2)',
              padding: '4px 10px',
              borderRadius: 'var(--r-full)',
              whiteSpace: 'nowrap',
            }}>
              <span style={{
                width: '6px', height: '6px',
                background: 'var(--color-brand)',
                borderRadius: '50%',
                flexShrink: 0,
              }} />
              Powered by Gemini
            </div>

            {/* Category dropdown */}
            <CategorySelector />
          </div>
        </div>

        {/* ── Content View routing (Chat vs Configuration) ── */}
        {activeView === 'config' ? (
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, background: 'var(--color-bg)', padding: '24px 24px 48px' }}>
            <div style={{ maxWidth: '960px', width: '100%', margin: '0 auto' }}>
              <ConfigManager />
            </div>
          </div>
        ) : (
          <>
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
                      style={{ width: '65%', height: '65%', objectFit: 'contain' }}
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

            {/* Input area */}
            <div className={s.inputArea}>
              <div className={s.inputBarWrap}>
                <div className={s.inputWrapper} style={{ flexDirection: 'column', alignItems: 'stretch', padding: '12px 14px' }}>
                  {/* Textarea occupies top */}
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
                    style={{ width: '100%', minHeight: '36px', maxHeight: '240px' }}
                  />

                  {/* Controls row occupies bottom */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '8px',
                    borderTop: '1px solid rgba(0, 0, 0, 0.05)',
                    paddingTop: '8px',
                  }}>
                    {/* Left: Status text if listening */}
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', flex: 1 }}>
                      {isListening ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#EF4444', fontWeight: '600' }}>
                          <span style={{
                            width: '8px',
                            height: '8px',
                            background: '#EF4444',
                            borderRadius: '50%',
                            display: 'inline-block',
                            animation: 'pulse 1.2s infinite'
                          }} />
                          Mendengarkan suara Anda...
                        </span>
                      ) : ''}
                    </div>

                    {/* Right: Mic + Send buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                      {/* Speech to text (Microphone) */}
                      <button
                        onClick={toggleListening}
                        disabled={loading}
                        title={isListening ? 'Hentikan mendengarkan' : 'Ketik dengan suara'}
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          border: 'none',
                          background: isListening ? '#EF4444' : 'rgba(0, 0, 0, 0.05)',
                          color: isListening ? '#ffffff' : 'var(--color-text-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                        onMouseEnter={e => { if (!isListening) e.currentTarget.style.background = 'rgba(0, 0, 0, 0.08)'; }}
                        onMouseLeave={e => { if (!isListening) e.currentTarget.style.background = 'rgba(0, 0, 0, 0.05)'; }}
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                          <line x1="12" y1="19" x2="12" y2="23" />
                          <line x1="8" y1="23" x2="16" y2="23" />
                        </svg>
                      </button>

                      {/* Send button */}
                      <button
                        id="chat-send-btn"
                        className={`${s.sendBtn}${loading ? ` ${s.sendBtnLoading}` : ''}`}
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        aria-label="Kirim"
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: 0,
                        }}
                      >
                        {loading ? <SpinnerIcon size={14} className={s.spinIcon} /> : <SendIcon size={14} />}
                      </button>
                    </div>
                  </div>
                </div>
                <p className={s.inputHint}>Enter untuk kirim · Shift+Enter untuk baris baru</p>
              </div>
            </div>
          </>
        )}

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
