// frontend/app/config/page.js
'use client';

import { useState } from 'react';
import ChatInterface from '../ChatInterface';
import ConfigManager from '../ConfigManager';

// ---- Inline SVG Icons ----
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

export default function ConfigPage() {
  const [subTab, setSubTab] = useState('umum'); // 'umum' or 'tata_kelola'

  return (
    <div style={{
      flex: '1',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-bg)',
      fontFamily: "'Inter', sans-serif",
      overflow: 'hidden'
    }}>
      {/* Tab Switcher Headers Container */}
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
        
        {/* Title */}
        <h2 style={{
          fontSize: '1.4rem',
          fontWeight: '700',
          color: 'var(--color-navy)',
          margin: 0
        }}>
          Konfigurasi Sistem
        </h2>

        {/* Tab Switcher Buttons (Globe / Gear) */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setSubTab('umum')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: subTab === 'umum' ? 'var(--color-accent-light)' : 'transparent',
              color: subTab === 'umum' ? 'var(--color-accent)' : 'var(--color-text-light)',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <GlobeIcon size={14} /> Umum
          </button>

          <button
            onClick={() => setSubTab('tata_kelola')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: subTab === 'tata_kelola' ? 'var(--color-accent-light)' : 'transparent',
              color: subTab === 'tata_kelola' ? 'var(--color-accent)' : 'var(--color-text-light)',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <GearIcon size={14} /> Tata Kelola
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div style={{ flex: '1', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {subTab === 'umum' ? (
          <ChatInterface hideHeader={true} />
        ) : (
          <div style={{
            flex: '1',
            overflowY: 'auto'
          }}>
            <div style={{
              maxWidth: '1000px',
              width: '100%',
              margin: '0 auto',
              padding: '10px 24px 24px 24px'
            }}>
              <ConfigManager />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
