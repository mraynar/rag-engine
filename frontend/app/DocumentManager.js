'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertCircleIcon, SpinnerIcon, TrashIcon, EyeIcon } from './icons';
import PreviewModal from './PreviewModal';
import s from './documents/documents.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

function TypeBadge({ type }) {
  const classMap = {
    txt:  s.typeTxt,
    csv:  s.typeCsv,
    xlsx: s.typeXlsx,
    xls:  s.typeXls,
    docx: s.typeDocx,
    pdf:  s.typePdf,
    pptx: s.typePptx,
    jpg:  s.typeImg,
    jpeg: s.typeImg,
    png:  s.typeImg,
    webp: s.typeImg,
  };
  const cls = classMap[type?.toLowerCase()] || s.typeDefault;
  return <span className={`${s.typeBadge} ${cls}`}>{type || '—'}</span>;
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function InboxIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"
      strokeLinejoin="round" className={s.emptyIcon} aria-hidden="true">
      <polyline points="21 8 21 21 3 21 3 8" />
      <rect x="1" y="3" width="22" height="5" />
      <line x1="10" y1="12" x2="14" y2="12" />
    </svg>
  );
}

function ConfirmDialog({ filename, onConfirm, onCancel, isDeleting }) {
  return (
    <div className={s.confirmOverlay} role="dialog" aria-modal="true"
      aria-labelledby="confirm-title">
      <div className={s.confirmDialog}>
        <p id="confirm-title" className={s.confirmTitle}>Delete Document</p>
        <p className={s.confirmBody}>
          Are you sure you want to delete{' '}
          <span className={s.confirmFilename}>{filename}</span>?
          {' '}All indexed chunks will be deleted from the vector store
          and cannot be recovered.
        </p>
        <div className={s.confirmActions}>
          <button className={s.cancelBtn} onClick={onCancel} disabled={isDeleting}>
            Cancel
          </button>
          <button className={s.confirmDeleteBtn} onClick={onConfirm} disabled={isDeleting}>
            {isDeleting
              ? <SpinnerIcon size={15} className={s.spin} />
              : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DocumentRow({ doc, onToggle, onDelete, onPreview, isToggling, deletingFilename, isSelected, onSelectToggle }) {
  const date = doc.uploaded_at
    ? new Date(doc.uploaded_at + 'Z').toLocaleDateString('en-US', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : '—';

  return (
    <div className={`${s.row} ${isSelected ? s.rowSelected : ''}`}>
      <div className={s.colCheck}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onSelectToggle(doc.filename)}
          aria-label={`Select ${doc.filename}`}
        />
      </div>

      <div className={s.colName}>
        <span className={s.filename}>{doc.filename}</span>
        <span className={s.fileLabel}>{doc.label || '—'}</span>
      </div>

      <div className={s.colType}>
        <TypeBadge type={doc.file_type} />
      </div>

      <div className={s.colChunks}>
        {doc.chunk_count?.toLocaleString() ?? '—'}
      </div>

      <div className={s.colDate}>{date}</div>

      <div className={s.colActive}>
        <button
          className={`${s.toggleTrack} ${doc.is_active ? s.toggleTrackActive : ''}`}
          onClick={() => onToggle(doc.filename, !doc.is_active)}
          disabled={isToggling}
          aria-label={`Toggle active state for ${doc.filename}`}
          aria-checked={doc.is_active}
          role="switch"
        >
          <span className={s.toggleThumb} />
        </button>
      </div>

      <div className={s.colActions}>
        <button
          className={s.previewBtn}
          onClick={() => onPreview(doc.filename)}
          aria-label={`Preview document ${doc.filename}`}
          title="Preview chunks"
        >
          <EyeIcon size={15} />
        </button>

        <button
          className={s.deleteBtn}
          onClick={() => onDelete(doc.filename)}
          disabled={deletingFilename === doc.filename}
          aria-label={`Delete ${doc.filename}`}
          title="Delete document"
        >
          <TrashIcon size={15} />
        </button>
      </div>
    </div>
  );
}

export default function DocumentManager() {
  const [documents, setDocuments]                 = useState([]);
  const [loadingDocs, setLoadingDocs]             = useState(true);
  const [fetchError, setFetchError]               = useState('');
  const [previewFilename, setPreviewFilename]     = useState(null);

  const [selectedFilenames, setSelectedFilenames] = useState([]);
  const [isBulkDeleting, setIsBulkDeleting]       = useState(false);

  const [togglingFilename, setTogglingFilename] = useState(null);
  const [pendingDelete, setPendingDelete]       = useState(null);
  const [deletingFilename, setDeletingFilename] = useState(null);

  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true);
    setFetchError('');
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (!res.ok) throw new Error('Failed to load document list.');
      setDocuments(await res.json());
    } catch (err) {
      setFetchError(err.message);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  async function handleToggle(filename, isActive) {
    setTogglingFilename(filename);
    try {
      const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to change document status.');
      }
      setDocuments(prev =>
        prev.map(d => d.filename === filename ? { ...d, is_active: isActive } : d)
      );
    } catch (err) {
      alert(err.message);
    } finally {
      setTogglingFilename(null);
    }
  }

  function handleDeleteRequest(filename) {
    setPendingDelete(filename);
  }

  async function handleDeleteConfirm() {
    if (!pendingDelete) return;
    setDeletingFilename(pendingDelete);
    try {
      const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(pendingDelete)}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete document.');
      }
      setSelectedFilenames(prev => prev.filter(x => x !== pendingDelete));
      setDocuments(prev => prev.filter(d => d.filename !== pendingDelete));
      setPendingDelete(null);
    } catch (err) {
      alert(err.message);
    } finally {
      setDeletingFilename(null);
    }
  }

  function handleDeleteCancel() {
    if (!deletingFilename) setPendingDelete(null);
  }

  const handleSelectAllToggle = () => {
    if (selectedFilenames.length === documents.length) {
      setSelectedFilenames([]);
    } else {
      setSelectedFilenames(documents.map(d => d.filename));
    }
  };

  const handleSelectToggle = (fn) => {
    setSelectedFilenames(prev =>
      prev.includes(fn) ? prev.filter(x => x !== fn) : [...prev, fn]
    );
  };

  const handleBulkDelete = async () => {
    if (selectedFilenames.length === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedFilenames.length} selected document(s)?`)) return;

    setIsBulkDeleting(true);
    try {
      for (const fn of selectedFilenames) {
        await fetch(`${API_BASE}/documents/${encodeURIComponent(fn)}`, { method: 'DELETE' });
      }
      setDocuments(prev => prev.filter(d => !selectedFilenames.includes(d.filename)));
      setSelectedFilenames([]);
    } catch (err) {
      alert('Bulk delete encountered an error: ' + err.message);
    } finally {
      setIsBulkDeleting(false);
    }
  };

  return (
    <div style={{ marginTop: '20px' }}>
      <div className={s.listSection}>
        <div className={s.listHeader} style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '10px' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--color-navy)' }}>Registered Documents (Manual)</h3>
          {!loadingDocs && (
            <span className={s.listCount}>
              {documents.length} document(s)
              {documents.filter(d => d.is_active).length > 0 &&
                `, ${documents.filter(d => d.is_active).length} active`}
            </span>
          )}
          {selectedFilenames.length > 0 && (
            <button
              onClick={handleBulkDelete}
              disabled={isBulkDeleting}
              style={{
                marginLeft: 'auto',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#E53E3E',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                fontWeight: '600',
                cursor: 'pointer',
                opacity: isBulkDeleting ? 0.7 : 1,
              }}
            >
              {isBulkDeleting ? 'Deleting...' : (
                <>
                  <TrashIcon size={12} /> Delete Selected ({selectedFilenames.length})
                </>
              )}
            </button>
          )}
        </div>

        {loadingDocs ? (
          <div className={s.emptyState}>
            <SpinnerIcon size={28} className={s.spin} />
          </div>
        ) : fetchError ? (
          <div className={s.errorMsg} role="alert">
            <AlertCircleIcon size={16} />
            {fetchError}
          </div>
        ) : documents.length === 0 ? (
          <div className={s.emptyState}>
            <InboxIcon />
            <p className={s.emptyTitle}>No documents yet</p>
            <p className={s.emptyBody}>
              Upload documents above to start indexing. The chatbot only searches active documents when category "All Data" is selected.
            </p>
          </div>
        ) : (
          <div className={s.tableWrapper} style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <table className={s.table}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ width: '40px', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={documents.length > 0 && selectedFilenames.length === documents.length}
                      onChange={toggleSelectAll}
                      style={{ cursor: 'pointer' }}
                    />
                  </th>
                  <th>Document</th>
                  <th>Format</th>
                  <th>Chunk</th>
                  <th>Uploaded</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map(doc => (
                  <DocumentRow
                    key={doc.filename}
                    doc={doc}
                    onToggle={handleToggle}
                    onDelete={handleDeleteRequest}
                    onPreview={setPreviewFilename}
                    togglingFilename={togglingFilename}
                    deletingFilename={deletingFilename}
                    isSelected={selectedFilenames.includes(doc.filename)}
                    onSelectToggle={() => toggleSelect(doc.filename)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {pendingDelete && (
        <ConfirmDialog
          filename={pendingDelete}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
          isDeleting={!!deletingFilename}
        />
      )}

      {/* Preview Modal */}
      <PreviewModal
        isOpen={!!previewFilename}
        onClose={() => setPreviewFilename(null)}
        type="manual"
        idOrFilename={previewFilename}
        title={previewFilename}
      />
    </div>
  );
}
