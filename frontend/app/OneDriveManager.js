'use client';

import { useState } from 'react';
import { useCategory } from './CategoryContext';
import { SpinnerIcon, TrashIcon, PencilIcon, CheckIcon, XIcon, PlusIcon, EyeIcon } from './icons';
import PreviewModal from './PreviewModal';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export default function OneDriveManager() {
  const { categories, refreshCategories } = useCategory();
  
  // States
  const [loading, setLoading] = useState(false);
  const [syncingId, setSyncingId] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);

  const toggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === categories.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(categories.map(c => c.id));
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected categories and all of their indexed data?`)) return;
    setIsBulkDeleting(true);
    try {
      for (const id of selectedIds) {
        const res = await fetch(`${API_BASE}/sources/${id}`, { method: 'DELETE' });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || `Failed to delete category ID ${id}`);
        }
      }
      alert('Successfully deleted selected categories.');
      setSelectedIds([]);
      refreshCategories();
    } catch (err) {
      alert(err.message);
      refreshCategories();
    } finally {
      setIsBulkDeleting(false);
    }
  };
  
  // Add Form Inputs
  const [categoryName, setCategoryName] = useState('');
  const [onedriveUrl, setOnedriveUrl] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  
  // Edit Form States
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editUrl, setEditUrl] = useState('');

  // Add category
  const handleAdd = async (e) => {
    e.preventDefault();
    if (!categoryName.trim() || !onedriveUrl.trim()) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${API_BASE}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_name: categoryName.trim(),
          onedrive_url: onedriveUrl.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to add category.');
      
      setCategoryName('');
      setOnedriveUrl('');
      setShowAddForm(false);
      refreshCategories();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Sync category
  const handleSync = async (id) => {
    setSyncingId(id);
    try {
      const res = await fetch(`${API_BASE}/sources/${id}/sync`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Synchronization failed.');
      alert(data.message || 'Synchronization successful.');
      refreshCategories();
    } catch (err) {
      alert(err.message);
      refreshCategories();
    } finally {
      setSyncingId(null);
    }
  };

  // Delete category
  const handleDelete = async (id, name) => {
    if (!confirm(`Are you sure you want to delete category "${name}"?`)) return;
    try {
      const res = await fetch(`${API_BASE}/sources/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete category.');
      }
      setSelectedIds(prev => prev.filter(x => x !== id));
      refreshCategories();
    } catch (err) {
      alert(err.message);
    }
  };

  // Start edit
  const startEdit = (cat) => {
    setEditingId(cat.id);
    setEditName(cat.category_name);
    setEditUrl(cat.onedrive_url);
  };

  // Save edit
  const saveEdit = async (id) => {
    if (!editName.trim() || !editUrl.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/sources/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_name: editName.trim(),
          onedrive_url: editUrl.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save changes.');
      
      setEditingId(null);
      refreshCategories();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div style={{ marginTop: '20px' }}>
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--color-navy)' }}>Online Data Source Categories</h3>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {selectedIds.length > 0 && (
              <button
                onClick={handleBulkDelete}
                disabled={isBulkDeleting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#E53E3E',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  opacity: isBulkDeleting ? 0.7 : 1,
                }}
              >
                {isBulkDeleting ? 'Deleting...' : (
                  <>
                    <TrashIcon size={12} /> Delete Selected ({selectedIds.length})
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'var(--color-accent)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.8rem',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              <PlusIcon size={12} /> Add Category
            </button>
          </div>
        </div>
        <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--color-muted)' }}>
          Link an online spreadsheet (OneDrive / Google Drive / Google Sheets) to a data category for precise semantic searches.
        </p>
      </div>

      {showAddForm && (
        <form onSubmit={handleAdd} style={{
          background: '#fff',
          border: '1px solid var(--color-border)',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '20px',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
        }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: 'var(--color-navy)' }}>Add New Category</h4>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
            <div style={{ flex: '1', minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: '4px' }}>Category Name</label>
              <input
                type="text"
                placeholder="Example: Vessel Service"
                value={categoryName}
                onChange={e => setCategoryName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--color-border)',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                }}
              />
            </div>
            <div style={{ flex: '2', minWidth: '300px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-muted)', marginBottom: '4px' }}>OneDrive / Google Drive / Google Sheets Share URL</label>
              <input
                type="url"
                placeholder="Example: https://1drv.ms/x/..., https://drive.google.com/..., or https://docs.google.com/spreadsheets/d/..."
                value={onedriveUrl}
                onChange={e => setOnedriveUrl(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid var(--color-border)',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                }}
              />
            </div>
          </div>
          {errorMsg && <p style={{ color: '#E53E3E', fontSize: '0.75rem', margin: '0 0 12px 0' }}>{errorMsg}</p>}
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              style={{
                background: 'none',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                backgroundColor: 'var(--color-navy)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                fontWeight: '600',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? <SpinnerIcon size={12} className="spin" /> : 'Save'}
            </button>
          </div>
        </form>
      )}

      <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden', maxHeight: '260px', overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--color-bg)', borderBottom: '1px solid var(--color-border)' }}>
              <th style={{ padding: '12px', width: '40px', textAlign: 'center' }}>
                <input
                  type="checkbox"
                  checked={categories.length > 0 && selectedIds.length === categories.length}
                  onChange={toggleSelectAll}
                  style={{ cursor: 'pointer' }}
                />
              </th>
              <th style={{ padding: '12px', color: 'var(--color-navy)', fontWeight: '600' }}>Category</th>
              <th style={{ padding: '12px', color: 'var(--color-navy)', fontWeight: '600' }}>Link / Share URL</th>
              <th style={{ padding: '12px', color: 'var(--color-navy)', fontWeight: '600' }}>Sync Status</th>
              <th style={{ padding: '12px', color: 'var(--color-navy)', fontWeight: '600', textAlign: 'center' }}>Chunk</th>
              <th style={{ padding: '12px', color: 'var(--color-navy)', fontWeight: '600', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((cat) => {
              const isEditing = editingId === cat.id;
              const isSyncing = syncingId === cat.id;
              
              let statusLabel = 'Not Synced';
              let statusColor = '#718096';
              let statusBg = '#EDF2F7';
              
              if (cat.sync_status === 'success') {
                statusLabel = 'Success';
                statusColor = '#38A169';
                statusBg = '#C6F6D5';
              } else if (cat.sync_status === 'failed') {
                statusLabel = 'Failed';
                statusColor = '#E53E3E';
                statusBg = '#FED7D7';
              }

              return (
                <tr key={cat.id} style={{ borderBottom: '1px solid var(--color-border)', transition: 'background 0.2s' }}>
                  {/* Select Checkbox */}
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(cat.id)}
                      onChange={() => toggleSelect(cat.id)}
                      style={{ cursor: 'pointer' }}
                    />
                  </td>
                  {/* Category Name */}
                  <td style={{ padding: '12px', fontWeight: '500' }}>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        style={{
                          padding: '6px',
                          border: '1px solid var(--color-border)',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          width: '100%',
                        }}
                      />
                    ) : (
                      cat.category_name
                    )}
                  </td>
                  
                  {/* OneDrive Link */}
                  <td style={{ padding: '12px', color: 'var(--color-text-light)', maxWidth: '300px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {isEditing ? (
                      <input
                        type="url"
                        value={editUrl}
                        onChange={e => setEditUrl(e.target.value)}
                        style={{
                          padding: '6px',
                          border: '1px solid var(--color-border)',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          width: '100%',
                        }}
                      />
                    ) : (
                      <a href={cat.onedrive_url} target="_blank" rel="noopener noreferrer" title={cat.onedrive_url} style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>
                        {cat.onedrive_url}
                      </a>
                    )}
                  </td>

                  {/* Status */}
                  <td style={{ padding: '12px' }}>
                    {isSyncing ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--color-muted)' }}>
                        <SpinnerIcon size={12} className="spin" /> Syncing...
                      </span>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', alignItems: 'center' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            fontWeight: '600',
                            color: statusColor,
                            backgroundColor: statusBg
                          }}>
                            {statusLabel}
                          </span>
                          {cat.sync_status === 'success' && cat.fetch_method && (() => {
                            let label = 'Mode: Graph API';
                            let color = '#2B6CB0';
                            let bgColor = '#EBF8FF';

                            if (cat.fetch_method === 'fallback_download') {
                              label = 'Mode: Fallback';
                              color = '#B7791F';
                              bgColor = '#FEFCBF';
                            } else if (cat.fetch_method === 'google_drive') {
                              label = 'Mode: Google Drive';
                              color = '#805AD5';
                              bgColor = '#FAF5FF';
                            } else if (cat.fetch_method === 'google_sheets') {
                              label = 'Mode: Google Sheets';
                              color = '#319795';
                              bgColor = '#E6FFFA';
                            }

                            return (
                              <span style={{
                                display: 'inline-block',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontSize: '0.7rem',
                                fontWeight: '600',
                                color: color,
                                backgroundColor: bgColor
                              }}>
                                {label}
                              </span>
                            );
                          })()}
                        </div>
                        {cat.last_synced_at && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--color-muted)' }}>
                            Sync: {new Date(cat.last_synced_at + 'Z').toLocaleDateString('en-US', {
                              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                            })}
                          </span>
                        )}
                        {cat.sync_status === 'failed' && cat.last_error && (
                          <span style={{ fontSize: '0.7rem', color: '#E53E3E', wordBreak: 'break-all' }} title={cat.last_error}>
                            Error: {cat.last_error.substring(0, 50)}...
                          </span>
                        )}
                      </div>
                    )}
                  </td>

                  {/* Chunk count */}
                  <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold' }}>
                    {cat.chunk_count?.toLocaleString('en-US') || 0}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => saveEdit(cat.id)}
                            style={{
                              padding: '6px 10px',
                              background: '#38A169',
                              border: 'none',
                              color: '#fff',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            <CheckIcon size={12} />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            style={{
                              padding: '6px 10px',
                              background: '#E2E8F0',
                              border: 'none',
                              color: 'var(--color-text)',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            <XIcon size={12} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => handleSync(cat.id)}
                            disabled={syncingId !== null}
                            style={{
                              padding: '6px 12px',
                              backgroundColor: 'var(--color-navy)',
                              color: '#fff',
                              border: 'none',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              cursor: 'pointer',
                              opacity: syncingId !== null ? 0.5 : 1,
                            }}
                          >
                            Sync
                          </button>
                          {cat.sync_status === 'success' && (
                            <button
                              onClick={() => setPreviewTarget({ id: cat.id, name: cat.category_name })}
                              style={{
                                padding: '6px 12px',
                                backgroundColor: '#EDF2F7',
                                color: 'var(--color-text)',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                              title="Preview synchronized data rows"
                            >
                              <EyeIcon size={12} /> Preview
                            </button>
                          )}
                          <button
                            onClick={() => startEdit(cat)}
                            style={{
                              padding: '6px 10px',
                              backgroundColor: '#EDF2F7',
                              border: 'none',
                              borderRadius: '4px',
                              color: 'var(--color-text)',
                              cursor: 'pointer',
                            }}
                          >
                            <PencilIcon size={12} />
                          </button>
                          <button
                            onClick={() => handleDelete(cat.id, cat.category_name)}
                            style={{
                              padding: '6px 10px',
                              backgroundColor: '#FED7D7',
                              border: 'none',
                              borderRadius: '4px',
                              color: '#E53E3E',
                              cursor: 'pointer',
                            }}
                          >
                            <TrashIcon size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {categories.length === 0 && (
              <tr>
                <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: 'var(--color-muted)' }}>
                  No categories registered yet. Please add an online data source category using the button in the top right.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* Extraction Preview Dialog */}
      <PreviewModal
        isOpen={!!previewTarget}
        onClose={() => setPreviewTarget(null)}
        type="cloud"
        idOrFilename={previewTarget?.id}
        title={previewTarget?.name}
      />
      
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
