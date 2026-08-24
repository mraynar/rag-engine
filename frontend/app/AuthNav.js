'use client';

import { useAuth } from './AuthContext';
import { useCategory } from './CategoryContext';

function LogInIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  );
}

function LogOutIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function UserIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export default function AuthNav() {
  const { user, loading, logout } = useAuth();
  const { setIsAuthModalOpen } = useCategory();

  if (loading) {
    return (
      <div style={{
        width: '80px',
        height: '32px',
        backgroundColor: 'var(--color-bg)',
        borderRadius: '6px',
        animation: 'pulse 1.5s infinite'
      }} />
    );
  }

  if (user) {
    const displayName = user.user_metadata?.display_name || user.email.split('@')[0];
    const shortName = displayName.length > 15 ? displayName.substring(0, 12) + '...' : displayName;

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Profile Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '20px',
          backgroundColor: '#EDF2F7',
          color: 'var(--color-text-light)',
          fontSize: '0.78rem',
          fontWeight: '600'
        }} title={user.email}>
          <UserIcon size={12} />
          <span>{shortName}</span>
        </div>

        {/* Logout Button */}
        <button
          onClick={logout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '6px',
            border: '1px solid var(--color-border)',
            color: 'var(--color-error)',
            fontWeight: '600',
            fontSize: '0.78rem',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title="Keluar dari akun"
        >
          <LogOutIcon size={12} />
          <span>Keluar</span>
        </button>
      </div>
    );
  }

  // Guest State
  return (
    <button
      onClick={() => setIsAuthModalOpen(true)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderRadius: '6px',
        backgroundColor: 'var(--color-navy)',
        color: '#fff',
        fontWeight: '600',
        fontSize: '0.78rem',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        boxShadow: 'var(--shadow-sm)'
      }}
      title="Masuk atau Daftar"
    >
      <LogInIcon size={12} />
      <span>Masuk / Daftar</span>
    </button>
  );
}
