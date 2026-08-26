'use client';

import { useState, useEffect } from 'react';
import { useCategory } from './CategoryContext';
import { SpinnerIcon, TrashIcon, PlusIcon, CheckIcon } from './icons';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

const getBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_BASE_URL) {
    return process.env.NEXT_PUBLIC_BASE_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return 'http://localhost:3000';
};

export default function AccessTokenManager() {
  const { categories } = useCategory();
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Form states
  const [categoryName, setCategoryName] = useState('');
  const [label, setLabel] = useState('');
  const [copiedToken, setCopiedToken] = useState(null);

  const fetchTokens = async () => {
    try {
      const res = await fetch(`${API_BASE}/access-tokens`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setTokens(data);
      } else {
        console.error('Failed to fetch tokens');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  // Pre-fill first category when list loads
  useEffect(() => {
    if (categories.length > 0 && !categoryName) {
      setCategoryName(categories[0].category_name);
    }
  }, [categories, categoryName]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!categoryName) return;
    setSubmitting(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${API_BASE}/access-tokens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_name: categoryName, label })
      });
      if (res.ok) {
        const newToken = await res.json();
        setTokens(prev => [newToken, ...prev]);
        setLabel('');
      } else {
        const errData = await res.json().catch(() => ({}));
        setErrorMsg(errData.detail || 'Failed to create token');
      }
    } catch (err) {
      setErrorMsg('Failed to create token due to network error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (id) => {
    if (!confirm('Are you sure you want to revoke this deep-link token? This action cannot be undone.')) return;
    try {
      const res = await fetch(`${API_BASE}/access-tokens/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setTokens(prev =>
          prev.map(t => t.id === id ? { ...t, revoked_at: new Date().toISOString() } : t)
        );
      } else {
        alert('Failed to revoke token');
      }
    } catch (err) {
      alert('Network error trying to revoke token');
    }
  };

  const handleCopy = (token) => {
    const origin = getBaseUrl();
    const url = `${origin}/access/${token}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedToken(token);
      setTimeout(() => setCopiedToken(null), 2000);
    }).catch(err => {
      console.error('Failed to copy', err);
    });
  };

  return (
    <div style={{ padding: '8px 4px 16px' }}>
      {/* Header Info */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 4px 0', fontSize: '1.05rem', color: 'var(--color-navy)', fontWeight: '700' }}>Deep-Link Tokens</h3>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-muted)' }}>
          Create secure, pre-configured access links for Power BI or company website buttons. Clicking the link automatically scopes the chatbot to a specific data category.
        </p>
      </div>

      {/* Form to Create Token */}
      <form onSubmit={handleCreate} style={{
        background: '#fff',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '20px',
        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
      }}>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: 'var(--color-navy)', fontWeight: '600' }}>Generate Access Link</h4>
        
        {errorMsg && (
          <div style={{ padding: '8px 12px', background: '#FEE2E2', border: '1px solid #FCA5A5', color: '#B91C1C', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '12px' }}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1', minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: '4px', fontWeight: '500' }}>Tabular Data Category</label>
            <select
              value={categoryName}
              onChange={e => setCategoryName(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                fontSize: '0.85rem',
                backgroundColor: '#fff',
                height: '38px',
                outline: 'none',
              }}
            >
              {categories.map(c => (
                <option key={c.id} value={c.category_name}>{c.category_name}</option>
              ))}
            </select>
          </div>

          <div style={{ flex: '2', minWidth: '300px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: '4px', fontWeight: '500' }}>Label / Description (e.g. Market Share Button)</label>
            <input
              type="text"
              placeholder="e.g. Power BI Report - Market Share page"
              value={label}
              onChange={e => setLabel(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                fontSize: '0.85rem',
                height: '38px',
                outline: 'none',
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting || categories.length === 0}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--color-accent)',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 16px',
            fontSize: '0.8rem',
            fontWeight: '600',
            cursor: submitting || categories.length === 0 ? 'not-allowed' : 'pointer',
            opacity: submitting || categories.length === 0 ? 0.7 : 1,
            transition: 'opacity 0.2s',
          }}
        >
          {submitting ? <SpinnerIcon size={12} /> : <PlusIcon size={12} />}
          Generate Link
        </button>
      </form>

      {/* Tokens List Table */}
      <div className="tableWrapper" style={{
        background: '#fff',
        border: '1px solid var(--color-border)',
        borderRadius: '8px',
        overflow: 'hidden',
        overflowX: 'auto',
        boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          textAlign: 'left',
          fontSize: '0.85rem',
          minWidth: '700px',
        }}>
          <thead>
            <tr style={{ backgroundColor: '#F8FAFC', borderBottom: '1px solid var(--color-border)' }}>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--color-muted)', width: '22%' }}>Label</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--color-muted)', width: '20%' }}>Category</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--color-muted)', width: '38%' }}>URL Access Link</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--color-muted)', width: '10%', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '12px 16px', fontWeight: '600', color: 'var(--color-muted)', width: '10%', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="5" style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                    <SpinnerIcon size={16} /> Loading tokens...
                  </div>
                </td>
              </tr>
            ) : tokens.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>
                  No deep-link tokens created yet.
                </td>
              </tr>
            ) : (
              tokens.map((t) => {
                const isRevoked = !!t.revoked_at;
                const base = getBaseUrl();
                const fullUrl = `${base}/access/${t.token}`;
                return (
                  <tr key={t.id} style={{
                    borderBottom: '1px solid var(--color-border)',
                    backgroundColor: isRevoked ? '#F8FAFC' : 'transparent',
                    color: isRevoked ? 'var(--color-text-faint)' : 'inherit',
                  }}>
                    <td style={{ padding: '12px 16px', fontWeight: '500' }}>{t.label || <span style={{ color: 'var(--color-text-faint)', fontStyle: 'italic' }}>No description</span>}</td>
                    <td style={{ padding: '12px 16px' }}>{t.category_name}</td>
                    <td style={{ padding: '12px 16px', position: 'relative' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontFamily: 'monospace',
                          fontSize: '0.8rem',
                          backgroundColor: isRevoked ? '#F1F5F9' : '#EFF6FF',
                          color: isRevoked ? 'var(--color-text-muted)' : 'var(--color-brand-dark)',
                          padding: '3px 6px',
                          borderRadius: '4px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: '220px',
                        }} title={fullUrl}>
                          {t.token}
                        </span>
                        
                        <button
                          onClick={() => handleCopy(t.token)}
                          disabled={isRevoked}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '26px',
                            height: '26px',
                            borderRadius: '4px',
                            border: '1px solid var(--color-border)',
                            backgroundColor: '#fff',
                            color: copiedToken === t.token ? '#10B981' : 'var(--color-text-muted)',
                            cursor: isRevoked ? 'not-allowed' : 'pointer',
                            opacity: isRevoked ? 0.5 : 1,
                            transition: 'all 0.2s',
                          }}
                          title="Copy Link to Clipboard"
                        >
                          {copiedToken === t.token ? (
                            <CheckIcon size={12} />
                          ) : (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                      {isRevoked ? (
                        <span style={{
                          fontSize: '0.75rem',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          backgroundColor: '#F1F5F9',
                          color: '#64748B',
                          fontWeight: '600',
                          display: 'inline-block'
                        }}>Revoked</span>
                      ) : (
                        <span style={{
                          fontSize: '0.75rem',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          backgroundColor: '#DCFCE7',
                          color: '#15803D',
                          fontWeight: '600',
                          display: 'inline-block'
                        }}>Active</span>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                      {!isRevoked ? (
                        <button
                          onClick={() => handleRevoke(t.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '6px',
                            border: '1px solid #FECACA',
                            borderRadius: '6px',
                            backgroundColor: '#FEF2F2',
                            color: '#EF4444',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={e => e.currentTarget.style.backgroundColor = '#FEE2E2'}
                          onMouseLeave={e => e.currentTarget.style.backgroundColor = '#FEF2F2'}
                          title="Revoke Token"
                        >
                          <TrashIcon size={14} />
                        </button>
                      ) : (
                        <span style={{ color: 'var(--color-text-faint)', fontSize: '0.8rem' }}>-</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
