'use client';

import { useState, useEffect } from 'react';
import { SpinnerIcon, XIcon, EyeIcon } from './icons';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

function ChevronLeftIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export default function PreviewModal({ isOpen, onClose, type, idOrFilename, title }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [activeSheet, setActiveSheet] = useState('');
  const limit = 50;

  useEffect(() => {
    if (!isOpen || !idOrFilename) return;
    fetchData();
  }, [isOpen, idOrFilename, page]);

  useEffect(() => {
    setPage(1);
    setData(null);
    setError('');
    setActiveSheet('');
  }, [idOrFilename, isOpen]);

  useEffect(() => {
    if (data?.sheets && data.sheets.length > 0 && !activeSheet) {
      setActiveSheet(data.sheets[0]);
    }
  }, [data, activeSheet]);

  async function fetchData() {
    setLoading(true);
    setError('');
    try {
      const offset = (page - 1) * limit;
      const endpoint = type === 'cloud'
        ? `${API_BASE}/sources/${idOrFilename}/preview?limit=${limit}&offset=${offset}`
        : `${API_BASE}/documents/${encodeURIComponent(idOrFilename)}/preview?limit=${limit}&offset=${offset}`;

      const res = await fetch(endpoint);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${res.status})`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('[PreviewModal] Fetch error:', err);
      setError(err.message || 'Failed to load preview data.');
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  const totalItems = type === 'cloud' ? (data?.total_rows || 0) : (data?.total_chunks || 0);
  const totalPages = Math.max(1, Math.ceil(totalItems / limit));

  const activeSheetRows = type === 'cloud' && data?.rows
    ? data.rows.filter(r => r.sheet_name === activeSheet)
    : [];

  const tableHeaders = activeSheetRows.length > 0
    ? Object.keys(activeSheetRows[0].row_data)
    : [];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(11, 47, 92, 0.45)',
      backdropFilter: 'blur(5px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{
        backgroundColor: '#fff',
        width: '92%',
        maxWidth: '1100px',
        height: '760px',
        maxHeight: '90vh',
        borderRadius: '12px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#FCFDFF',
          flexShrink: 0
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <EyeIcon size={18} style={{ color: 'var(--color-navy)' }} />
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: 'var(--color-navy)', fontWeight: '700' }}>
                Extraction Data Preview
              </h3>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: 'var(--color-muted)' }}>
              {type === 'cloud' ? 'Spreadsheet Row Records' : 'ChromaDB Text Chunks'} for: <strong style={{ color: 'var(--color-text)' }}>{title}</strong>
            </p>
          </div>
          
          <button
            onClick={onClose}
            style={{
              padding: '6px',
              borderRadius: '50%',
              backgroundColor: '#EDF2F7',
              color: 'var(--color-text-light)',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.2s'
            }}
            title="Close preview"
          >
            <XIcon size={15} />
          </button>
        </div>

        {/* Sheet Tabs */}
        {type === 'cloud' && data?.sheets && data.sheets.length > 0 && (
          <div style={{
            padding: '8px 24px 0',
            display: 'flex',
            gap: '6px',
            backgroundColor: '#F8FAFC',
            borderBottom: '1px solid var(--color-border)',
            overflowX: 'auto',
            flexShrink: 0
          }}>
            {data.sheets.map(sheet => (
              <button
                key={sheet}
                onClick={() => setActiveSheet(sheet)}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderBottom: activeSheet === sheet ? '3px solid var(--color-navy)' : '3px solid transparent',
                  backgroundColor: 'transparent',
                  color: activeSheet === sheet ? 'var(--color-navy)' : 'var(--color-text-light)',
                  fontWeight: '600',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"></line>
                  <line x1="12" y1="20" x2="12" y2="4"></line>
                  <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                {sheet}
              </button>
            ))}
          </div>
        )}

        {/* Body content */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          backgroundColor: '#F8FAFC',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {loading && !data ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
              <SpinnerIcon size={32} className="spin" style={{ color: 'var(--color-navy)' }} />
              <span style={{ fontSize: '0.85rem', color: 'var(--color-muted)' }}>Loading extraction content...</span>
            </div>
          ) : error ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px', textAlign: 'center' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#E53E3E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <h4 style={{ margin: '12px 0 6px 0', color: '#E53E3E' }}>Failed to Load Preview</h4>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-muted)' }}>{error}</p>
            </div>
          ) : totalItems === 0 ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px', textAlign: 'center', backgroundColor: '#fff', borderRadius: '8px', border: '1px dashed var(--color-border)' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-navy)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <h4 style={{ margin: '12px 0 6px 0', color: 'var(--color-navy)' }}>No Data Found</h4>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--color-muted)', maxWidth: '400px' }}>
                This source has not been indexed or does not contain any readable records. If this is a cloud spreadsheet, please trigger a <strong>Sync</strong> first.
              </p>
            </div>
          ) : (
            <>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                {type === 'cloud' ? (
                  <div style={{
                    backgroundColor: '#fff',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                    overflow: 'auto',
                    flex: 1
                  }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                      <thead>
                        <tr style={{ background: 'var(--color-bg)', borderBottom: '2px solid var(--color-border)', position: 'sticky', top: 0, zIndex: 1 }}>
                          <th style={{ padding: '10px 12px', color: 'var(--color-navy)', fontWeight: '700', width: '60px', textAlign: 'center', borderRight: '1px solid var(--color-border)' }}>Row</th>
                          {tableHeaders.map(h => (
                            <th key={h} style={{ padding: '10px 12px', color: 'var(--color-navy)', fontWeight: '700', borderRight: '1px solid var(--color-border)' }}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {activeSheetRows.map((row, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: idx % 2 === 0 ? '#fff' : '#F9FBFD' }}>
                            <td style={{ padding: '8px 12px', color: 'var(--color-muted)', textAlign: 'center', fontWeight: '600', borderRight: '1px solid var(--color-border)', backgroundColor: '#F8FAFC' }}>
                              {row.row_index + 1}
                            </td>
                            {tableHeaders.map(h => (
                              <td key={h} style={{ padding: '8px 12px', borderRight: '1px solid var(--color-border)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: '250px' }} title={row.row_data[h] !== null ? String(row.row_data[h]) : ''}>
                                {row.row_data[h] !== null ? String(row.row_data[h]) : <em style={{ color: '#CBD5E0' }}>null</em>}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', flex: 1 }}>
                    {data?.chunks?.map((chunk, idx) => (
                      <div key={chunk.id} style={{
                        backgroundColor: '#fff',
                        border: '1px solid var(--color-border)',
                        borderRadius: '8px',
                        padding: '16px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px dashed #EDF2F7', paddingBottom: '6px' }}>
                          <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--color-accent)', backgroundColor: '#EBF8FF', padding: '2px 8px', borderRadius: '4px' }}>
                            Chunk #{((page - 1) * limit) + idx + 1}
                          </span>
                          <span style={{ fontSize: '0.72rem', color: 'var(--color-muted)' }}>
                            ID: <code style={{ backgroundColor: '#EDF2F7', padding: '1px 4px', borderRadius: '3px' }}>{chunk.id.substring(0, 16)}...</code>
                          </span>
                          {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                            <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem', color: 'var(--color-muted)' }}>
                              {chunk.metadata.page !== undefined && (
                                <span style={{ backgroundColor: '#F0FFF4', color: '#2F855A', padding: '2px 6px', borderRadius: '4px', fontWeight: '600' }}>
                                  Page {chunk.metadata.page}
                                </span>
                              )}
                              {chunk.metadata.sheet !== undefined && (
                                <span style={{ backgroundColor: '#FAF5FF', color: '#6B46C1', padding: '2px 6px', borderRadius: '4px', fontWeight: '600' }}>
                                  Sheet: {chunk.metadata.sheet}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <p style={{
                          margin: 0,
                          fontSize: '0.8375rem',
                          lineHeight: '1.5',
                          color: 'var(--color-text)',
                          whiteSpace: 'pre-wrap',
                          fontFamily: "'Courier New', Courier, monospace"
                        }}>
                          {chunk.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Pagination */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingTop: '16px',
                borderTop: '1px solid var(--color-border)',
                marginTop: '16px',
                flexShrink: 0
              }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-muted)' }}>
                  Showing {((page - 1) * limit) + 1} - {Math.min(page * limit, totalItems)} of <strong>{totalItems.toLocaleString('en-US')}</strong> records
                </span>
                
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    disabled={page === 1 || loading}
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: '1px solid var(--color-border)',
                      backgroundColor: '#fff',
                      color: page === 1 ? '#CBD5E0' : 'var(--color-text)',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      cursor: page === 1 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    <ChevronLeftIcon size={14} /> Previous
                  </button>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text)' }}>
                    Page <strong>{page}</strong> of {totalPages}
                  </span>
                  <button
                    disabled={page === totalPages || loading}
                    onClick={() => setPage(p => p + 1)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: '1px solid var(--color-border)',
                      backgroundColor: '#fff',
                      color: page === totalPages ? '#CBD5E0' : 'var(--color-text)',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      cursor: page === totalPages ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Next <ChevronRightIcon size={14} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

      </div>
      <style jsx global>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
