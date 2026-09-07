'use client';

import { useState } from 'react';
import { useConversation } from './ConversationContext';
import { TrashIcon, ChatIcon } from './icons';

function PinIcon({ size = 15, filled = false }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="17" x2="12" y2="22" />
      <path d="M5 17h14v-1.76a2 2 0 0 0-.51-1.37l-1.49-1.61V5a2 2 0 0 0-2-2H10a2 2 0 0 0-2 2v7.26l-1.49 1.61A2 2 0 0 0 6 15.24V17z" fill={filled ? 'currentColor' : 'none'} />
    </svg>
  );
}

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
  return parsedDate.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function ActivityManager({ onSelectConv }) {
  const {
    conversations,
    deleteConversation,
    deleteAllConversations,
    togglePin,
  } = useConversation();

  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // 'all' | 'pinned'
  const [showConfirmDeleteAll, setShowConfirmDeleteAll] = useState(false);
  const [deletingAll, setDeletingAll] = useState(false);

  const filteredConvs = conversations.filter(c => {
    const matchesSearch = c.title.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' ? true : c.pinned;
    return matchesSearch && matchesFilter;
  });

  const handleDeleteOne = async (e, id, title) => {
    e.stopPropagation();
    if (window.confirm(`Delete conversation "${title}"?`)) {
      await deleteConversation(id);
    }
  };

  const handleDeleteAll = async () => {
    setDeletingAll(true);
    await deleteAllConversations();
    setDeletingAll(false);
    setShowConfirmDeleteAll(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
      {/* Confirm Delete All Modal */}
      {showConfirmDeleteAll && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(4px)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            maxWidth: '440px',
            width: '100%',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
            border: '1px solid #E2E8F0',
            animation: 'scaleUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{
                width: '40px', height: '40px', borderRadius: '50%',
                background: '#FEE2E2', color: '#DC2626',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <TrashIcon size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: '#0F172A' }}>
                  Clear All History?
                </h3>
                <p style={{ margin: '2px 0 0', fontSize: '0.8rem', color: '#64748B' }}>
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <p style={{ fontSize: '0.88rem', color: '#334155', lineHeight: '1.5', marginBottom: '24px' }}>
              All your conversation history ({conversations.length} items) will be permanently deleted from the system.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowConfirmDeleteAll(false)}
                disabled={deletingAll}
                style={{
                  padding: '9px 16px',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  background: '#ffffff',
                  color: '#475569',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAll}
                disabled={deletingAll}
                style={{
                  padding: '9px 18px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#DC2626',
                  color: '#ffffff',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {deletingAll ? 'Deleting...' : 'Delete All'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header section */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        borderBottom: '1px solid var(--color-border)',
        paddingBottom: '16px'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: '700', color: 'var(--color-text-strong)' }}>
            Activity & Conversation History
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            Manage and clear your conversation history with TPS Assistant.
          </p>
        </div>

        {conversations.length > 0 && (
          <button
            onClick={() => setShowConfirmDeleteAll(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 16px',
              borderRadius: '8px',
              background: '#FEE2E2',
              color: '#DC2626',
              border: '1px solid #FCA5A5',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#FCA5A5'}
            onMouseLeave={e => e.currentTarget.style.background = '#FEE2E2'}
          >
            <TrashIcon size={16} />
            <span>Clear All History</span>
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setFilter('all')}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: '600',
              border: 'none',
              background: filter === 'all' ? 'var(--color-brand)' : 'rgba(0,0,0,0.06)',
              color: filter === 'all' ? '#ffffff' : 'var(--color-text-muted)',
              cursor: 'pointer'
            }}
          >
            All ({conversations.length})
          </button>
          <button
            onClick={() => setFilter('pinned')}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: '600',
              border: 'none',
              background: filter === 'pinned' ? 'var(--color-brand)' : 'rgba(0,0,0,0.06)',
              color: filter === 'pinned' ? '#ffffff' : 'var(--color-text-muted)',
              cursor: 'pointer'
            }}
          >
            Pinned ({conversations.filter(c => c.pinned).length})
          </button>
        </div>

        <input
          type="text"
          placeholder="Search conversation history..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--color-border)',
            fontSize: '0.85rem',
            width: '240px',
            outline: 'none',
            background: 'var(--color-surface)'
          }}
        />
      </div>

      {/* History List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
        {filteredConvs.length === 0 ? (
          <div style={{
            padding: '48px 24px',
            textAlign: 'center',
            background: 'var(--color-surface)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-muted)'
          }}>
            <p style={{ margin: 0, fontSize: '0.95rem', fontWeight: '500' }}>
              {search ? 'No conversations match your search.' : 'No conversation history yet.'}
            </p>
          </div>
        ) : (
          filteredConvs.map(conv => (
            <div
              key={conv.id}
              onClick={() => onSelectConv && onSelectConv(conv.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 18px',
                borderRadius: '12px',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--color-brand)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--color-border)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', overflow: 'hidden' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '10px',
                  background: 'rgba(0, 114, 206, 0.08)', color: 'var(--color-brand)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <ChatIcon size={18} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--color-text-strong)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {conv.title}
                    </span>
                    {conv.pinned && (
                      <span style={{
                        fontSize: '0.7rem', fontWeight: '600', background: '#FEF3C7', color: '#D97706',
                        padding: '2px 8px', borderRadius: '10px', flexShrink: 0
                      }}>
                        Pinned
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                    {relativeTime(conv.updated_at)}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                <button
                  title={conv.pinned ? 'Unpin conversation' : 'Pin conversation'}
                  onClick={(e) => {
                    e.stopPropagation();
                    togglePin(conv.id, !conv.pinned);
                  }}
                  style={{
                    padding: '6px',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'transparent',
                    color: conv.pinned ? '#D97706' : 'var(--color-text-muted)',
                    cursor: 'pointer'
                  }}
                >
                  <PinIcon size={15} filled={conv.pinned} />
                </button>
                <button
                  title="Delete conversation"
                  onClick={(e) => handleDeleteOne(e, conv.id, conv.title)}
                  style={{
                    padding: '6px',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'transparent',
                    color: '#EF4444',
                    cursor: 'pointer'
                  }}
                >
                  <TrashIcon size={15} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
