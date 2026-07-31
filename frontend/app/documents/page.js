// frontend/app/documents/page.js
'use client';

import OneDriveManager from '../OneDriveManager';

export default function DocumentsPage() {
  return (
    <div style={{
      flex: '1',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--color-bg)',
      fontFamily: "'Inter', sans-serif",
      overflowY: 'auto'
    }}>
      <div style={{
        maxWidth: '1000px',
        width: '100%',
        margin: '0 auto',
        padding: '24px'
      }}>
        <OneDriveManager />
      </div>
    </div>
  );
}
