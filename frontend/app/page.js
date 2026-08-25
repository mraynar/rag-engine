'use client';

import ChatInterface from './ChatInterface';

export default function UnifiedPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <ChatInterface hideHeader={true} showSidebar={true} />
    </div>
  );
}
