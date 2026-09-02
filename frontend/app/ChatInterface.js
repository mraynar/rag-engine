'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
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
  const hasTimezone = isoStr.endsWith('Z') || isoStr.includes('+') || /[-+]\d{2}:\d{2}$/.test(isoStr);
  const dateStr = hasTimezone ? isoStr : isoStr + 'Z';
  const parsedDate = new Date(dateStr);
  if (isNaN(parsedDate.getTime())) return '';
  const diff = Date.now() - parsedDate.getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)   return 'Just now';
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return 'Yesterday';
  if (d < 7)   return `${d}d ago`;
  return parsedDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

// ─── Thinking indicator ───────────────────────────────────────────────────────

function ThinkingIndicator() {
  return (
    <div className={s.msgRow}>
      <div className={s.thinkingRow} aria-label="AI is processing...">
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
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ role, content, sources, debug }) {
  const isUser = role === 'user';
  const [debugOpen, setDebugOpen] = useState(false);

  // Separate main content from embedded debug text
  let mainContent = content || '';
  let legacyDebugText = '';
  if (!isUser && mainContent.includes('\n---\n### Debug Information')) {
    const parts = mainContent.split('\n---\n### Debug Information');
    mainContent = parts[0];
    legacyDebugText = '### Debug Information' + parts[1];
  } else if (!isUser && mainContent.includes('---') && mainContent.includes('Debug Information')) {
    const parts = mainContent.split('---');
    for (let idx = 0; idx < parts.length; idx++) {
      if (parts[idx].includes('Debug Information')) {
        mainContent = parts.slice(0, idx).join('---');
        legacyDebugText = parts.slice(idx).join('---');
        if (!legacyDebugText.startsWith('###')) legacyDebugText = '### ' + legacyDebugText.trim();
        break;
      }
    }
  }

  if (isUser) {
    return (
      <div className={s.msgRow}>
        <div className={s.msgRowUserInner}>
          <div className={`${s.avatar} ${s.avatarUser}`} aria-hidden="true">U</div>
          <div className={s.userBubble}>{mainContent}</div>
        </div>
      </div>
    );
  }

  const hasDebugObject = debug && typeof debug === 'object' && Object.keys(debug).length > 0;
  const hasLegacyDebug = Boolean(legacyDebugText);
  const showDebugToggle = hasDebugObject || hasLegacyDebug;

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
          <div className={s.aiSender}>TPS Assistant</div>
          <div className={s.markdownContent}>
            <ReactMarkdown>{mainContent}</ReactMarkdown>
          </div>

          {showDebugToggle && (
            <div className={s.debugWrapper}>
              <button
                className={s.debugToggle}
                onClick={() => setDebugOpen(o => !o)}
                aria-expanded={debugOpen}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                  strokeLinejoin="round" style={{ marginRight: 5 }}>
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {debugOpen ? 'Sembunyikan Debug Query' : 'Lihat Debug Query'}
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ marginLeft: 5, transform: debugOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              {debugOpen && (
                hasDebugObject ? (
                  <div className={s.debugPanel}>
                    <div className={s.debugSection}>
                      <span className={s.debugLabel}>📊 Dataset</span>
                      <span className={s.debugValue}>
                        {debug.routing?.selected || debug.routing?.dataset || debug.category || '—'}
                      </span>
                    </div>
                    <div className={s.debugSection}>
                      <span className={s.debugLabel}>🔍 Routing</span>
                      <span className={s.debugValue}>
                        {debug.routing?.method || '—'} {debug.routing?.confidence ? `(confidence: ${(debug.routing.confidence * 100).toFixed(0)}%)` : ''}
                      </span>
                    </div>
                    {debug.routing?.reason && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>💡 Alasan</span>
                        <span className={s.debugValue}>{debug.routing.reason}</span>
                      </div>
                    )}
                    {debug.query_plan?.sheet && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>📋 Sheet</span>
                        <span className={s.debugValue}>{debug.query_plan.sheet}</span>
                      </div>
                    )}
                    {debug.query_plan?.filters?.length > 0 && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>🔎 Filter</span>
                        <span className={s.debugValue}>{debug.query_plan.filters.join(' AND ')}</span>
                      </div>
                    )}
                    {debug.query_plan?.aggregation && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>📐 Aggregasi</span>
                        <span className={s.debugValue}>{debug.query_plan.aggregation}</span>
                      </div>
                    )}
                    {debug.query_plan?.path && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>⚙️ Path</span>
                        <span className={s.debugValue} style={{color: debug.query_plan.path === 'llm_fallback' ? '#f59e0b' : '#10b981'}}>
                          {debug.query_plan.path === 'llm_fallback' ? '🤖 LLM Query Builder' : '⚡ Deterministic'}
                        </span>
                      </div>
                    )}
                    {debug.execution?.steps && Object.keys(debug.execution.steps).length > 0 && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>📈 Hasil</span>
                        <span className={s.debugValue}>
                          {Object.entries(debug.execution.steps).map(([k, v]) =>
                            `Step ${k}: ${v.quality} (${v.row_count} rows)`
                          ).join(' | ')}
                        </span>
                      </div>
                    )}
                    {debug.query_plan?.deterministic_error && (
                      <div className={s.debugSection}>
                        <span className={s.debugLabel}>⚠️ Fallback</span>
                        <span className={s.debugValue} style={{color: '#f59e0b', fontSize: '0.7rem'}}>
                          {debug.query_plan.deterministic_error}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className={s.debugPanel}>
                    <div className={s.markdownContent}>
                      <ReactMarkdown>{legacyDebugText}</ReactMarkdown>
                    </div>
                  </div>
                )
              )}
            </div>
          )}

          {sources && sources.length > 0 && (
            <div className={s.sourcesRow} aria-label="Document sources">
              <span className={s.sourcesLabel}>Sources:</span>
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
          aria-label="Rename conversation"
        />
      ) : (
        <span className={s.convTitle} title={conv.title}>{conv.title}</span>
      )}

      <span className={s.convTime}>{relativeTime(conv.updated_at)}</span>

      {(hovered || isActive) && !renaming && (
        <button
          className={s.convMenuBtn}
          title="Options"
          onClick={(e) => {
            e.stopPropagation();
            const rect = e.currentTarget.getBoundingClientRect();
            // Position context menu underneath the button
            setContextMenu({ x: rect.left, y: rect.bottom + window.scrollY });
          }}
          aria-label="Options"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="12" cy="5" r="1.5" />
            <circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
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
              label: conv.pinned ? 'Unpin' : 'Pin',
              icon: <PinIcon size={12} filled={conv.pinned} />,
              onClick: () => { onPin(conv.id, !conv.pinned); setContextMenu(null); },
              danger: false,
            },
            {
              label: 'Rename',
              icon: <PencilIcon size={12} />,
              onClick: () => { setDraftTitle(conv.title); setRenaming(true); setContextMenu(null); },
              danger: false,
            },
            {
              label: 'Delete',
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
  const router = useRouter();

  const [shake, setShake] = useState(false);
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setIsAccountMenuOpen(false);
      }
    }
    if (isAccountMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isAccountMenuOpen]);

  const pinned   = conversations.filter(c => c.pinned);
  const unpinned = conversations.filter(c => !c.pinned);

  async function handleDelete(id) {
    if (!window.confirm('Delete this conversation?')) return;
    await deleteConversation(id);
  }

  return (
    <nav className={s.sidebar} aria-label="Conversation history">
      {/* Header with rounded White Card for TPS Logo and Close button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 14px 12px',
        borderBottom: '1px solid var(--sidebar-border)',
        flexShrink: 0
      }}>
        {/* Container for TPS Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          height: '32px'
        }}>
          <img
            src="/images/Logo%20TPS%20Monokrom.png"
            alt="Logo TPS"
            style={{ height: '100%', width: 'auto', objectFit: 'contain' }}
          />
        </div>

        {/* Sidebar Close Button */}
        <button
          onClick={() => setSidebarOpen(false)}
          title="Close history"
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
            if (typeof window !== 'undefined' && window.innerWidth <= 640) {
              setSidebarOpen(false);
            }
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
          <PlusIcon size={14} /> New conversation
        </button>
      </div>

      {/* Conversations List (Riwayat) */}
      <div className={s.convList} role="list">
        {pinned.length > 0 && (
          <>
            <div className={s.convGroupLabel} aria-hidden="true">Pinned</div>
            {pinned.map(conv => (
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId && activeView === 'chat'}
                onSelect={(id) => {
                  setActiveView('chat');
                  setActiveConvId(id);
                  if (typeof window !== 'undefined' && window.innerWidth <= 640) {
                    setSidebarOpen(false);
                  }
                }}
                onRename={renameConversation}
                onPin={togglePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {unpinned.length > 0 && (
          <>
            {pinned.length > 0 && <div className={s.convGroupLabel} aria-hidden="true">Recent</div>}
            {unpinned.map(conv => (
              <ConvItem key={conv.id} conv={conv} isActive={conv.id === activeConvId && activeView === 'chat'}
                onSelect={(id) => {
                  setActiveView('chat');
                  setActiveConvId(id);
                  if (typeof window !== 'undefined' && window.innerWidth <= 640) {
                    setSidebarOpen(false);
                  }
                }}
                onRename={renameConversation}
                onPin={togglePin}
                onDelete={handleDelete}
              />
            ))}
          </>
        )}

        {conversations.length === 0 && (
          <div className={s.convEmpty}>Start a new conversation to see history here.</div>
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
          onClick={() => {
            setActiveView('config');
            if (typeof window !== 'undefined' && window.innerWidth <= 640) {
              setSidebarOpen(false);
            }
          }}
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
          <span>Settings</span>
        </button>

        {/* Auth status block */}
        {authLoading ? (
          <div style={{ height: '36px', background: 'rgba(255,255,255,0.08)', borderRadius: 'var(--r-sm)', animation: 'pulse 1.5s infinite' }} />
        ) : user ? (
          <div ref={accountMenuRef} style={{ position: 'relative', width: '100%' }}>
            {/* Account Popover Menu */}
            {isAccountMenuOpen && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 'calc(100% + 8px)',
                  left: 0,
                  right: 0,
                  backgroundColor: '#ffffff',
                  borderRadius: '10px',
                  boxShadow: '0 12px 30px rgba(0, 0, 0, 0.2), 0 2px 6px rgba(0, 0, 0, 0.08)',
                  border: '1px solid #E2E8F0',
                  padding: '6px',
                  zIndex: 1000,
                }}
              >
                {/* Account Details Header */}
                <div style={{ padding: '8px 10px 10px', borderBottom: '1px solid #F1F5F9' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    Signed in as
                  </div>
                  <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user.user_metadata?.display_name || user.email.split('@')[0]}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748B', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user.email}
                  </div>
                </div>

                {/* Menu Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setIsAccountMenuOpen(false);
                      logout();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      background: 'none',
                      border: 'none',
                      fontSize: '0.82rem',
                      fontWeight: '500',
                      color: '#1E293B',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = '#F8FAFC'}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                      <circle cx="9" cy="7" r="4" />
                      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                    </svg>
                    <span>Change Account</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIsAccountMenuOpen(false);
                      logout();
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      background: 'none',
                      border: 'none',
                      fontSize: '0.82rem',
                      fontWeight: '500',
                      color: '#DC2626',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = '#FEF2F2'}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}

            {/* Profile Card trigger button */}
            <div
              onClick={() => setIsAccountMenuOpen(!isAccountMenuOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: 'var(--r-sm)',
                background: isAccountMenuOpen ? 'rgba(255, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                gap: '8px',
                width: '100%',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                if (!isAccountMenuOpen) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.14)';
              }}
              onMouseLeave={e => {
                if (!isAccountMenuOpen) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
              }}
              title="Click to manage account"
            >
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
                  <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.7)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '130px' }}>
                    {user.email}
                  </span>
                </div>
              </div>

              {/* Chevron Icon */}
              <div
                style={{
                  padding: '4px',
                  borderRadius: 'var(--r-sm)',
                  color: 'rgba(255, 255, 255, 0.85)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transform: isAccountMenuOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease',
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="18 15 12 9 6 15" />
                </svg>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => router.push('/login')}
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
            <span>Sign In</span>
          </button>
        )}
      </div>
    </nav>
  );
}

// ─── Main Chat Interface Inner ───────────────────────────────────────────────

function ChatInterfaceInner({ hideHeader = false, showSidebar = true }) {
  const { selectedCategory, setSelectedCategory } = useCategory();
  const { user } = useAuth();
  const {
    activeConvId, setActiveConvId,
    conversations, loadingConvs,
    loadConversations,
    createConversation, getConversation, getCachedConversation, postChatMessage,
  } = useConversation();

  const searchParams = useSearchParams();
  const queryConvId = searchParams.get('conversation_id');
  const queryCategoryName = searchParams.get('category_name');

  const [messages, setMessages] = useState([]);
  const [loadingMsgHistory, setLoadingMsgHistory] = useState(false);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeView, setActiveView]   = useState('chat'); // 'chat' or 'config'
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.innerWidth <= 640) {
      setSidebarOpen(false);
    }
  }, []);

  useEffect(() => {
    if (loadingConvs) return;
    if (queryConvId) {
      setActiveConvId(queryConvId);
      if (queryCategoryName) {
        setSelectedCategory(queryCategoryName);
      }
      
      // If guest mode, bootstrap the conversation in localStorage if not exists
      if (!user) {
        try {
          const stored = localStorage.getItem('rag_guest_conversations');
          const guestConvs = stored ? JSON.parse(stored) : [];
          const exists = guestConvs.some(c => c.id === queryConvId);
          if (!exists) {
            const newConv = {
              id: queryConvId,
              title: queryCategoryName || 'New conversation',
              title_source: 'auto',
              pinned: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              category_name: queryCategoryName,
              messages: []
            };
            guestConvs.push(newConv);
            localStorage.setItem('rag_guest_conversations', JSON.stringify(guestConvs));
            loadConversations();
          }
        } catch (e) {
          console.error('Error bootstrapping guest conversation:', e);
        }
      }
      
      window.history.replaceState(null, '', '/');
    }
  }, [loadingConvs, queryConvId, queryCategoryName, setActiveConvId, setSelectedCategory, user, loadConversations]);

  const loadedConvRef = useRef(null);
  const bottomRef     = useRef(null);
  const messagesContainerRef = useRef(null);
  const inputRef      = useRef(null);
  const recognitionRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const isUserScrolledUpRef = useRef(false);

  const handleMessagesScroll = () => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const isScrolledUp = distanceFromBottom > 120;
    isUserScrolledUpRef.current = isScrolledUp;
    setShowScrollBottom(isScrolledUp);
  };

  const scrollToBottom = (smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  // Auto-scroll only on new message sent/received (never fighting manual scroll)
  const prevMsgCountRef = useRef(0);
  useEffect(() => {
    if (activeView === 'chat') {
      const isNewMsg = messages.length > prevMsgCountRef.current;
      if (isNewMsg || !isUserScrolledUpRef.current) {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    }
    prevMsgCountRef.current = messages.length;
  }, [messages.length, activeView]);

  // Bootstrap active conversation
  useEffect(() => {
    if (loadingConvs || activeConvId) return;
    if (conversations.length > 0) {
      const empty = conversations.find(c => c.message_count === 0);
      setActiveConvId(empty ? empty.id : conversations[0].id);
    } else {
      createConversation().then(data => { if (data?.id) setActiveConvId(data.id); });
    }
  }, [loadingConvs, activeConvId, conversations, createConversation, setActiveConvId]);

  // Load messages instantly from cache, then sync from server
  useEffect(() => {
    if (!activeConvId) return;
    setInput(getDraft(activeConvId));

    // 1. Instant synchronous cache check — 0ms transition, no welcome screen flash
    const cached = getCachedConversation(activeConvId);
    if (cached && Array.isArray(cached.messages)) {
      setMessages(cached.messages.map(m => ({
        role: m.role === 'assistant' ? 'ai' : 'user',
        content: m.content,
        sources: m.sources || [],
      })));
      loadedConvRef.current = activeConvId;
    } else {
      // Not in cache yet: check if it's a known empty conversation or newly created
      const convMeta = conversations.find(c => c.id === activeConvId);
      if (convMeta && convMeta.message_count === 0) {
        setMessages([]);
        loadedConvRef.current = activeConvId;
      }
    }

    // 2. Fetch fresh data from server in background
    let isCurrent = true;
    getConversation(activeConvId)
      .then(data => {
        if (!isCurrent || !data) return;
        loadedConvRef.current = activeConvId;
        setMessages(data.messages.map(m => ({
          role: m.role === 'assistant' ? 'ai' : 'user',
          content: m.content,
          sources: m.sources || [],
        })));
      })
      .catch(() => {});

    return () => {
      isCurrent = false;
    };
  }, [activeConvId, getConversation, getCachedConversation]);


  // Auto-resize textarea height as content changes (max ~40% of viewport)
  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    const maxH = Math.floor(window.innerHeight * 0.40);
    if (!input) {
      // Empty: reset to single-line default
      textarea.style.height = '';
    } else {
      textarea.style.height = '0px';
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxH)}px`;
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
    // If currently already on an empty conversation, simply reset view
    if (messages.length === 0 && activeConvId) {
      return true;
    }
    const data = await createConversation();
    if (!data) return false;
    setActiveConvId(data.id);
    setMessages([]);
    return true;
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setLoading(true);
    setError(null);

    let convId = activeConvId;
    if (!convId) {
      try {
        const newConv = await createConversation();
        if (newConv?.id) {
          convId = newConv.id;
          setActiveConvId(convId);
        } else {
          throw new Error('Failed to initialize conversation session.');
        }
      } catch (err) {
        console.error('[handleSend] Conv creation error:', err);
        setError(err.message || 'Could not start conversation.');
        setLoading(false);
        return;
      }
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');
    if (convId) setDraft(convId, '');

    try {
      const data = await postChatMessage(convId, text, selectedCategory);
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources || [], debug: data.debug || null }]);
      await loadConversations();
    } catch (err) {
      console.error('[handleSend] Chat post error:', err);
      setError(err.message || 'Failed to connect to server.');
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
      {/* Mobile backdrop */}
      {showSidebar && sidebarOpen && (
        <div
          className={s.mobileSidebarBackdrop}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
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
                title="Show history"
                aria-label="Open sidebar"
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

            <span className={s.chatInnerTitle}>
              TPS Assistant
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Powered by Gemini Badge */}
            <div className={s.geminiBadge}>
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
              ref={messagesContainerRef}
              onScroll={handleMessagesScroll}
              className={s.chatMessages}
              role="log"
              aria-live="polite"
              aria-label="Conversation"
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
                  <p className={s.emptyTitle}>Welcome to TPS Assistant</p>
                  <p className={s.emptyDesc}>
                    Ask anything about Terminal Petikemas Surabaya services.
                    I am ready to help you.
                  </p>
                </div>
              )}

              {messages.map((msg, i) => (
                <MessageBubble key={i} role={msg.role} content={msg.content} sources={msg.sources} debug={msg.debug} />
              ))}

              {loading && <ThinkingIndicator />}

              {error && (
                <div className={s.errorBanner} role="alert">
                  <AlertCircleIcon size={16} />
                  <span>{error}</span>
                  <button className={s.errorClose} onClick={() => setError(null)} aria-label="Close">
                    <XIcon size={14} />
                  </button>
                </div>
              )}

              <div ref={bottomRef} aria-hidden="true" />
            </div>

            {showScrollBottom && (
              <button
                onClick={() => scrollToBottom(true)}
                style={{
                  position: 'absolute',
                  bottom: '105px',
                  right: '24px',
                  zIndex: 25,
                  background: 'var(--color-brand)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '20px',
                  padding: '7px 15px',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.18)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'transform 0.15s ease, background 0.15s ease',
                }}
              >
                ↓ Ke bawah
              </button>
            )}

            {/* Input area */}
            <div className={s.inputArea}>
              <div className={s.inputBarWrap}>
                <div className={s.inputWrapper} style={{
                  flexDirection: 'column',
                  alignItems: 'stretch',
                  padding: '10px 16px 8px 16px',
                  borderRadius: '24px',
                  border: '1.5px solid var(--color-border)',
                  boxShadow: 'var(--shadow-md)',
                  background: 'var(--color-surface)',
                }}>
                  {/* Textarea occupies top */}
                  <textarea
                    ref={inputRef}
                    id="chat-input"
                    className={s.textarea}
                    rows={1}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message..."
                    disabled={loading}
                    aria-label="Chat input"
                    style={{ width: '100%' }}
                  />

                  {/* Controls row occupies bottom */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '4px',
                    paddingTop: '0px',
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
                          Listening...
                        </span>
                      ) : ''}
                    </div>

                    {/* Right: Mic + Send buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexShrink: 0 }}>
                      {/* Speech to text (Microphone) */}
                      <button
                        onClick={toggleListening}
                        disabled={loading}
                        title={isListening ? 'Stop listening' : 'Voice typing'}
                        style={{
                          width: '42px',
                          height: '42px',
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
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
                        aria-label="Send"
                        style={{
                          width: '42px',
                          height: '42px',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: 0,
                          backgroundColor: loading || !input.trim() ? 'rgba(0, 0, 0, 0.04)' : 'var(--color-brand)',
                          color: loading || !input.trim() ? 'var(--color-text-faint)' : '#ffffff',
                          border: 'none',
                          cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        {loading ? <SpinnerIcon size={18} className={s.spinIcon} /> : <SendIcon size={18} />}
                      </button>
                    </div>
                  </div>
                </div>
                <p className={s.inputHint}>TPS Assistant can make mistakes. AI Assistant of PT Terminal Petikemas Surabaya.</p>
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
