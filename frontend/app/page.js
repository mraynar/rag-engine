'use client';

import { useState } from 'react';
import ChatInterface from './ChatInterface';
import ConfigManager from './ConfigManager';
import { useCategory } from './CategoryContext';

function GlobeIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
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

export default function UnifiedPage() {
  const [activeTab, setActiveTab] = useState('umum');
  const { selectedCategory } = useCategory();

  return (
    <div style={{
      flex: '1',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-bg)',
      fontFamily: "'Inter', sans-serif",
      overflow: 'hidden',
    }}>
      <div style={{
        maxWidth: '1120px',
        width: '100%',
        margin: '0 auto',
        padding: '16px 24px 8px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        flexShrink: 0,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: '700', color: 'var(--color-navy)', margin: 0 }}>
              TPS Chatbot
            </h2>
            <button style={{
              background: 'none', border: 'none',
              color: 'var(--color-muted)', cursor: 'pointer',
              padding: '4px', display: 'flex', alignItems: 'center',
            }} title="System Information">
              <InfoIcon size={16} />
            </button>
          </div>

          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => setActiveTab('umum')}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '6px 12px', borderRadius: '6px', border: 'none',
                backgroundColor: activeTab === 'umum' ? 'var(--color-accent-light)' : 'transparent',
                color: activeTab === 'umum' ? 'var(--color-accent)' : 'var(--color-text-light)',
                fontWeight: '600', fontSize: '0.8rem', cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <GlobeIcon size={14} /> Chat
            </button>
            <button
              onClick={() => setActiveTab('konfigurasi')}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '6px 12px', borderRadius: '6px', border: 'none',
                backgroundColor: activeTab === 'konfigurasi' ? 'var(--color-accent-light)' : 'transparent',
                color: activeTab === 'konfigurasi' ? 'var(--color-accent)' : 'var(--color-text-light)',
                fontWeight: '600', fontSize: '0.8rem', cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <GearIcon size={14} /> Configuration
            </button>
          </div>
        </div>

        <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-muted)' }}>
          {activeTab === 'umum' ? (
            <>Chat Mode: Inquiries based on internal TPS documentation (Active Category: <strong style={{ color: 'var(--color-navy)' }}>{selectedCategory}</strong>)</>
          ) : (
            <>Configuration Mode: Manage AI API keys, embedding/generation models, and Microsoft Graph credentials</>
          )}
        </p>
      </div>

      <div style={{ flex: '1', display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
        {activeTab === 'umum' ? (
          <ChatInterface hideHeader={true} showSidebar={true} />
        ) : (
          <div style={{ flex: '1', overflowY: 'auto', minHeight: 0 }}>
            <div style={{ maxWidth: '1000px', width: '100%', margin: '0 auto', padding: '10px 24px 24px 24px' }}>
              <ConfigManager />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
