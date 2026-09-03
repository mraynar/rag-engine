'use client';

import { useState, useEffect, useCallback } from 'react';
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

function TableIcon({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="12" y1="3" x2="12" y2="21" />
    </svg>
  );
}

const LIMIT = 50;

export default function PreviewModal({ isOpen, onClose, type, idOrFilename, title }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [activeSheet, setActiveSheet] = useState('');
  const [sheetCounts, setSheetCounts] = useState({});

  // Reset state whenever source changes or modal reopens
  useEffect(() => {
    setPage(1);
    setData(null);
    setError('');
    setActiveSheet('');
    setSheetCounts({});
  }, [idOrFilename, isOpen]);

  // Core fetch function
  const fetchData = useCallback(async (sheetParam, pageParam) => {
    if (!isOpen || !idOrFilename) return;
    setLoading(true);
    setError('');
    try {
      const offset = (pageParam - 1) * LIMIT;

      let endpoint;
      if (type === 'cloud') {
        const sheetQuery = sheetParam ? `&sheet=${encodeURIComponent(sheetParam)}` : '';
        endpoint = `${API_BASE}/sources/${idOrFilename}/preview?limit=${LIMIT}&offset=${offset}${sheetQuery}`;
      } else {
        endpoint = `${API_BASE}/documents/${encodeURIComponent(idOrFilename)}/preview?limit=${LIMIT}&offset=${offset}`;
      }

      const res = await fetch(endpoint);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${res.status})`);
      }
      const json = await res.json();
      setData(json);

      // Sync sheet counts from response
      if (json.sheet_counts) setSheetCounts(json.sheet_counts);

      // Set active sheet if not yet set
      if (!sheetParam && json.active_sheet) {
        setActiveSheet(json.active_sheet);
      }
    } catch (err) {
      console.error('[PreviewModal] Fetch error:', err);
      setError(err.message || 'Failed to load preview data.');
    } finally {
      setLoading(false);
    }
  }, [isOpen, idOrFilename, type]);

  // Fetch when page changes (initial load uses page=1, activeSheet='')
  useEffect(() => {
    if (!isOpen || !idOrFilename) return;
    fetchData(activeSheet || undefined, page);
  }, [page, isOpen, idOrFilename]);

  // Switch sheet tab: reset page, refetch
  const handleSheetSwitch = (sheet) => {
    if (sheet === activeSheet) return;
    setActiveSheet(sheet);
    setPage(1);
    fetchData(sheet, 1);
  };

  if (!isOpen) return null;

  const totalItems = type === 'cloud' ? (data?.total_rows || 0) : (data?.total_chunks || 0);
  const totalPages = Math.max(1, Math.ceil(totalItems / LIMIT));

  // For cloud: rows are already filtered by active_sheet from the server
  const tableRows = type === 'cloud' ? (data?.rows || []) : [];

  // Build headers - filter out internal metadata cols
  const rawHeaders = tableRows.length > 0 ? Object.keys(tableRows[0].row_data) : [];
  const visibleHeaders = rawHeaders.filter(h => !h.startsWith('_') || h === '_sheet');

  // Hide all-null columns among current page rows
  const nonNullHeaders = visibleHeaders.filter(h =>
    tableRows.some(row => row.row_data[h] !== null && row.row_data[h] !== undefined && row.row_data[h] !== '')
  );
  const tableHeaders = nonNullHeaders.length > 0 ? nonNullHeaders : visibleHeaders;

  const sheetsAvailable = data?.sheets || [];

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
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

        {/* ── Header ─────────────────────────────────────── */}
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
              {type === 'cloud' ? 'Spreadsheet Row Records' : 'ChromaDB Text Chunks'} for:{' '}
              <strong style={{ color: 'var(--color-text)' }}>{title}</strong>
              {type === 'cloud' && data?.total_rows_global > 0 && (
                <span style={{ marginLeft: '8px', fontWeight: 400 }}>
                  — {(data.total_rows_global).toLocaleString('id-ID')} total baris
                </span>
              )}
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              padding: '6px', borderRadius: '50%', backgroundColor: '#EDF2F7',
              color: 'var(--color-text-light)', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background-color 0.2s'
            }}
            title="Tutup preview"
          >
            <XIcon size={15} />
          </button>
        </div>

        {/* ── Sheet Tabs ─────────────────────────────────── */}
        {type === 'cloud' && sheetsAvailable.length > 0 && (
          <div style={{
            padding: '0 24px',
            display: 'flex',
            gap: '2px',
            backgroundColor: '#F8FAFC',
            borderBottom: '1px solid var(--color-border)',
            overflowX: 'auto',
            flexShrink: 0
          }}>
            {sheetsAvailable.map(sheet => {
              const isActive = activeSheet === sheet;
              const cnt = sheetCounts[sheet];
              return (
                <button
                  key={sheet}
                  onClick={() => handleSheetSwitch(sheet)}
                  style={{
                    padding: '10px 14px',
                    border: 'none',
                    borderBottom: isActive ? '3px solid var(--color-navy)' : '3px solid transparent',
                    backgroundColor: 'transparent',
                    color: isActive ? 'var(--color-navy)' : 'var(--color-text-light)',
                    fontWeight: isActive ? '700' : '500',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'color 0.15s',
                  }}
                >
                  <TableIcon size={11} />
                  {sheet}
                  {cnt != null && (
                    <span style={{
                      fontSize: '0.68rem',
                      backgroundColor: isActive ? 'var(--color-navy)' : '#E2E8F0',
                      color: isActive ? '#fff' : '#718096',
                      borderRadius: '10px',
                      padding: '1px 6px',
                      fontWeight: '600',
                    }}>
                      {cnt.toLocaleString('id-ID')}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* ── Body ───────────────────────────────────────── */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 24px',
          backgroundColor: '#F8FAFC',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {loading && !data ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
              <SpinnerIcon size={32} className="spin" style={{ color: 'var(--color-navy)' }} />
              <span style={{ fontSize: '0.85rem', color: 'var(--color-muted)' }}>Memuat data preview...</span>
            </div>
          ) : error ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px', textAlign: 'center' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#E53E3E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <h4 style={{ margin: '12px 0 6px 0', color: '#E53E3E' }}>Gagal Memuat Preview</h4>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-muted)' }}>{error}</p>
            </div>
          ) : totalItems === 0 && !loading ? (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px', textAlign: 'center', backgroundColor: '#fff', borderRadius: '8px', border: '1px dashed var(--color-border)' }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-navy)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <h4 style={{ margin: '12px 0 6px 0', color: 'var(--color-navy)' }}>Tidak Ada Data</h4>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--color-muted)', maxWidth: '400px' }}>
                Sumber ini belum diindeks atau tidak memiliki data yang dapat dibaca. Jika ini adalah spreadsheet cloud, lakukan <strong>Sync</strong> terlebih dahulu.
              </p>
            </div>
          ) : (
            <>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, position: 'relative' }}>
                {/* Loading overlay saat ganti sheet/halaman */}
                {loading && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    backgroundColor: 'rgba(248,250,252,0.75)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 5, borderRadius: '8px'
                  }}>
                    <SpinnerIcon size={24} className="spin" style={{ color: 'var(--color-navy)' }} />
                  </div>
                )}

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
                          <th style={{ padding: '10px 12px', color: 'var(--color-navy)', fontWeight: '700', width: '56px', textAlign: 'center', borderRight: '1px solid var(--color-border)' }}>Row</th>
                          {tableHeaders.map(h => (
                            <th key={h} style={{ padding: '10px 12px', color: 'var(--color-navy)', fontWeight: '700', borderRight: '1px solid var(--color-border)', whiteSpace: 'nowrap' }}>
                              {h === '_sheet' ? 'SUMBER_SHEET' : h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tableRows.map((row, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: idx % 2 === 0 ? '#fff' : '#F9FBFD' }}>
                            <td style={{ padding: '8px 12px', color: 'var(--color-muted)', textAlign: 'center', fontWeight: '600', borderRight: '1px solid var(--color-border)', backgroundColor: '#F8FAFC' }}>
                              {row.row_index + 1}
                            </td>
                            {tableHeaders.map(h => (
                              <td
                                key={h}
                                style={{ padding: '8px 12px', borderRight: '1px solid var(--color-border)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', maxWidth: '250px' }}
                                title={row.row_data[h] !== null && row.row_data[h] !== undefined ? String(row.row_data[h]) : ''}
                              >
                                {(row.row_data[h] !== null && row.row_data[h] !== undefined && row.row_data[h] !== '')
                                  ? String(row.row_data[h])
                                  : <em style={{ color: '#CBD5E0' }}>—</em>
                                }
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
                            Chunk #{((page - 1) * LIMIT) + idx + 1}
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
                          margin: 0, fontSize: '0.8375rem', lineHeight: '1.5',
                          color: 'var(--color-text)', whiteSpace: 'pre-wrap',
                          fontFamily: "'Courier New', Courier, monospace"
                        }}>
                          {chunk.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ── Pagination ─────────────────────────────── */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                paddingTop: '14px',
                borderTop: '1px solid var(--color-border)',
                marginTop: '14px',
                flexShrink: 0
              }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-muted)' }}>
                  Menampilkan{' '}
                  <strong>{((page - 1) * LIMIT) + 1}</strong>{' – '}
                  <strong>{Math.min(page * LIMIT, totalItems)}</strong>
                  {' dari '}
                  <strong>{totalItems.toLocaleString('id-ID')}</strong>
                  {' baris'}
                  {activeSheet && (
                    <span style={{ marginLeft: '6px' }}>
                      (sheet <strong style={{ color: 'var(--color-navy)' }}>{activeSheet}</strong>)
                    </span>
                  )}
                </span>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    disabled={page === 1 || loading}
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '4px',
                      padding: '6px 12px', borderRadius: '6px',
                      border: '1px solid var(--color-border)', backgroundColor: '#fff',
                      color: page === 1 ? '#CBD5E0' : 'var(--color-text)',
                      fontSize: '0.8rem', fontWeight: '600',
                      cursor: page === 1 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    <ChevronLeftIcon size={14} /> Previous
                  </button>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-text)' }}>
                    Halaman <strong>{page}</strong> dari {totalPages}
                  </span>
                  <button
                    disabled={page === totalPages || loading}
                    onClick={() => setPage(p => p + 1)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '4px',
                      padding: '6px 12px', borderRadius: '6px',
                      border: '1px solid var(--color-border)', backgroundColor: '#fff',
                      color: page === totalPages ? '#CBD5E0' : 'var(--color-text)',
                      fontSize: '0.8rem', fontWeight: '600',
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
