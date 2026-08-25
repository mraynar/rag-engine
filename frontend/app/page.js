'use client';

import { useState } from 'react';
import ChatInterface from './ChatInterface';
import ConfigManager from './ConfigManager';
import { useCategory } from './CategoryContext';

// ─── Tab Icons ────────────────────────────────────────────────────────────────

function ChatIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function GearIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

const TABS = [
  { id: 'chat', label: 'Chat', Icon: ChatIcon },
  { id: 'config', label: 'Configuration', Icon: GearIcon },
];

export default function UnifiedPage() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>

      {/* Sub-tab bar — sits just below topnav */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        borderBottom: '1px solid var(--color-border-soft)',
        background: 'var(--color-surface)',
        flexShrink: 0,
        gap: '2px',
        height: '42px',
      }}>
        {TABS.map(({ id, label, Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '6px 12px',
                borderRadius: 'var(--r-sm)',
                border: 'none',
                background: active ? 'var(--color-brand-light)' : 'transparent',
                color: active ? 'var(--color-brand)' : 'var(--color-text-muted)',
                fontWeight: active ? '600' : '500',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                letterSpacing: '-0.005em',
                fontFamily: 'inherit',
              }}
              aria-current={active ? 'page' : undefined}
            >
              <Icon size={14} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Page content — full remaining height */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {activeTab === 'chat' ? (
          <ChatInterface hideHeader={true} showSidebar={true} />
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, background: 'var(--color-bg)' }}>
            <div style={{ maxWidth: '960px', width: '100%', margin: '0 auto', padding: '24px 24px 48px' }}>
              <ConfigManager />
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
