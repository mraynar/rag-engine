'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function AccessPage() {
  const router = useRouter();
  const params = useParams();
  const token = params.token;
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    async function resolve() {
      try {
        const res = await fetch(`/api/proxy/access/${token}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Access link is invalid or has been revoked.');
        }
        const data = await res.json();
        
        // Redirect to chat page with query params
        router.replace(`/?conversation_id=${data.conversation_id}&category_name=${encodeURIComponent(data.category_name)}`);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }

    resolve();
  }, [token, router]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      backgroundColor: '#F8FAFC',
      fontFamily: "'Inter', -apple-system, sans-serif",
      padding: '20px',
      textAlign: 'center'
    }}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div className="spinner" style={{
            width: '40px',
            height: '40px',
            border: '4px solid #E2E8F0',
            borderTop: '4px solid #1C6BBF',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <span style={{ fontSize: '0.9rem', color: '#4A5568', fontWeight: '500' }}>Resolving deep-link access...</span>
        </div>
      ) : error ? (
        <div style={{ maxWidth: '400px', backgroundColor: '#fff', padding: '32px', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '16px' }}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h3 style={{ margin: '0 0 8px 0', color: '#1A202C', fontWeight: '700', fontSize: '1.2rem' }}>Access Link Invalid</h3>
          <p style={{ margin: '0 0 24px 0', fontSize: '0.85rem', color: '#64748B', lineHeight: '1.5' }}>{error}</p>
          <button
            onClick={() => router.replace('/')}
            style={{
              backgroundColor: '#1C6BBF',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 20px',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = '#155090'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = '#1C6BBF'}
          >
            Go to Home Page
          </button>
        </div>
      ) : null}

      <style jsx global>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
