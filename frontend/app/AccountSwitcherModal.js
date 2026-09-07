'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './AuthContext';
import { XIcon, SpinnerIcon } from './icons';

export default function AccountSwitcherModal({ isOpen, onClose }) {
  const { user, savedAccounts, switchAccount, removeSavedAccount } = useAuth();
  const router = useRouter();
  const [switchingId, setSwitchingId] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSelectAccount = async (acc) => {
    if (acc.id === user?.id) {
      onClose();
      return;
    }
    setSwitchingId(acc.id);
    setError(null);
    try {
      const res = await switchAccount(acc);
      if (res?.error) {
        setError('Account session expired. Please log in again.');
        setTimeout(() => {
          router.push(`/login?email=${encodeURIComponent(acc.email)}`);
        }, 1200);
      } else {
        onClose();
      }
    } catch (err) {
      setError('Failed to switch account: ' + (err.message || 'An error occurred'));
    } finally {
      setSwitchingId(null);
    }
  };

  const handleAddNewAccount = () => {
    onClose();
    router.push('/login');
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(15, 23, 42, 0.65)',
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
        maxWidth: '460px',
        width: '100%',
        padding: '24px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.22)',
        border: '1px solid #E2E8F0',
        animation: 'scaleUp 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
        position: 'relative'
      }}>
        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            border: 'none',
            background: '#F1F5F9',
            color: '#64748B',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <XIcon size={16} />
        </button>

        {/* Modal Header */}
        <div style={{ marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: '700', color: '#0F172A' }}>
            Switch Account
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: '#64748B' }}>
            Select a saved account to access its conversations & data.
          </p>
        </div>

        {error && (
          <div style={{
            background: '#FEF2F2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '10px 14px',
            borderRadius: '8px',
            fontSize: '0.82rem',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        {/* Accounts List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto', marginBottom: '20px' }}>
          {savedAccounts.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#64748B', fontSize: '0.85rem' }}>
              No other saved accounts on this device.
            </div>
          ) : (
            savedAccounts.map((acc) => {
              const isActive = acc.id === user?.id;
              const isSwitching = switchingId === acc.id;
              const displayName = acc.display_name || acc.email.split('@')[0];

              return (
                <div
                  key={acc.id}
                  onClick={() => handleSelectAccount(acc)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderRadius: '12px',
                    border: isActive ? '2px solid var(--color-brand)' : '1px solid #E2E8F0',
                    background: isActive ? 'rgba(0, 114, 206, 0.05)' : '#ffffff',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => {
                    if (!isActive) e.currentTarget.style.borderColor = '#94A3B8';
                  }}
                  onMouseLeave={e => {
                    if (!isActive) e.currentTarget.style.borderColor = '#E2E8F0';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
                    <div style={{
                      width: '36px', height: '36px', borderRadius: '50%',
                      background: 'var(--color-brand)', color: '#ffffff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: '700', fontSize: '0.9rem', flexShrink: 0
                    }}>
                      {displayName[0].toUpperCase()}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {displayName}
                        </span>
                        {isActive && (
                          <span style={{
                            fontSize: '0.68rem', fontWeight: '700', background: '#DBEAFE', color: '#1E40AF',
                            padding: '2px 8px', borderRadius: '10px', flexShrink: 0
                          }}>
                            Active
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: '0.78rem', color: '#64748B', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {acc.email}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    {isSwitching && <SpinnerIcon size={18} />}
                    {!isActive && (
                      <button
                        title="Remove from this device"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeSavedAccount(acc.id);
                        }}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          color: '#94A3B8',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: '4px'
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = '#EF4444'}
                        onMouseLeave={e => e.currentTarget.style.color = '#94A3B8'}
                      >
                        <XIcon size={14} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Add new account button */}
        <button
          onClick={handleAddNewAccount}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '10px',
            border: '1.5px dashed var(--color-brand)',
            background: 'rgba(0, 114, 206, 0.03)',
            color: 'var(--color-brand)',
            fontWeight: '600',
            fontSize: '0.88rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(0, 114, 206, 0.08)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(0, 114, 206, 0.03)'}
        >
          <span>+ Add Another Account</span>
        </button>
      </div>
    </div>
  );
}
