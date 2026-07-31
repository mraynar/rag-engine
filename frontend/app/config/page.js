// frontend/app/config/page.js
'use client';

import ConfigManager from '../ConfigManager';

export default function ConfigPage() {
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
      {/* Header Container */}
      <div style={{
        maxWidth: '1000px',
        width: '100%',
        margin: '0 auto',
        padding: '24px 24px 10px 24px',
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
      </div>

      {/* Content Area - Scrollable for the config items list */}
      <div style={{ flex: '1', overflowY: 'auto' }}>
        <div style={{
          maxWidth: '1000px',
          width: '100%',
          margin: '0 auto',
          padding: '10px 24px 24px 24px'
        }}>
          <ConfigManager />
        </div>
      </div>
    </div>
  );
}
