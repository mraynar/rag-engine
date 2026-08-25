'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircleIcon, CheckCircleIcon, SpinnerIcon, TrashIcon } from './icons';
import { useUpload } from './UploadContext';
import s from './documents/documents.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

const SUPPORTED_ACCEPT = '.txt,.csv,.xlsx,.xls,.docx,.pdf,.pptx,.jpg,.jpeg,.png,.webp';
const SUPPORTED_LABEL  = '.txt, .csv, .xlsx, .xls, .docx, .pdf, .pptx, .jpg, .jpeg, .png, .webp';

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

function UploadCloudIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
      strokeLinejoin="round" className={s.dropZoneIcon} aria-hidden="true">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
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

function DocumentRow({ doc, onToggle, onDelete, togglingFilename, deletingFilename, isSelected, onSelectToggle }) {
  const isToggling = togglingFilename === doc.filename;
  const date = doc.uploaded_at
    ? new Date(doc.uploaded_at + 'Z').toLocaleDateString('en-US', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : '—';

  return (
    <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
      {/* Checkbox column */}
      <td style={{ padding: '12px', textAlign: 'center' }}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelectToggle}
          style={{ cursor: 'pointer' }}
        />
      </td>
      <td>
        <span className={s.filename} title={doc.filename}>{doc.filename}</span>
        {doc.label && doc.label !== doc.filename && (
          <span className={s.labelText}>{doc.label}</span>
        )}
      </td>
      <td><TypeBadge type={doc.file_type} /></td>
      <td><span className={s.chunkCount}>{doc.chunk_count?.toLocaleString('en-US')}</span></td>
      <td><span className={s.dateText}>{date}</span></td>
      <td className={s.toggleCell}>
        <label className={s.toggleLabel}>
          <input
            type="checkbox"
            className={s.toggleCheckbox}
            checked={doc.is_active}
            disabled={true}
            id={`toggle-${doc.filename}`}
            aria-label={`Activate ${doc.filename}`}
          />
          {isToggling && <SpinnerIcon size={13} className={s.spin} />}
        </label>
      </td>
      <td>
        <button
          className={s.deleteBtn}
          onClick={() => onDelete(doc.filename)}
          disabled={!!deletingFilename}
          aria-label={`Delete ${doc.filename}`}
          title="Delete document"
          id={`delete-${doc.filename.replace(/\./g, '-')}`}
        >
          <TrashIcon size={15} />
        </button>
      </td>
    </tr>
  );
}

export default function DocumentManager() {
  const [documents, setDocuments]         = useState([]);
  const [loadingDocs, setLoadingDocs]     = useState(true);
  const [fetchError, setFetchError]       = useState('');
  const [selectedFilenames, setSelectedFilenames] = useState([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const toggleSelect = (filename) => {
    setSelectedFilenames(prev =>
      prev.includes(filename) ? prev.filter(x => x !== filename) : [...prev, filename]
    );
  };

  const toggleSelectAll = () => {
    if (selectedFilenames.length === documents.length) {
      setSelectedFilenames([]);
    } else {
      setSelectedFilenames(documents.map(d => d.filename));
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedFilenames.length} selected documents and all of their indexed data?`)) return;
    setIsBulkDeleting(true);
    try {
      for (const filename of selectedFilenames) {
        const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || `Failed to delete document ${filename}`);
        }
      }
      alert('Successfully deleted selected documents.');
      setSelectedFilenames([]);
      fetchDocuments();
    } catch (err) {
      alert(err.message);
      fetchDocuments();
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const [selectedFile, setSelectedFile]   = useState(null);
  const [label, setLabel]                 = useState('');
  const [isDragOver, setIsDragOver]       = useState(false);

  const [togglingFilename, setTogglingFilename] = useState(null);
  const [pendingDelete, setPendingDelete]       = useState(null);
  const [deletingFilename, setDeletingFilename] = useState(null);

  const fileInputRef = useRef(null);
  const { startUpload, registerRefreshCallback, unregisterRefreshCallback } = useUpload();

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

  useEffect(() => {
    registerRefreshCallback(fetchDocuments);
    return () => unregisterRefreshCallback();
  }, [fetchDocuments, registerRefreshCallback, unregisterRefreshCallback]);

  function handleFileSelect(file) {
    if (!file) return;
    setSelectedFile(file);
  }

  function handleInputChange(e) {
    handleFileSelect(e.target.files?.[0] || null);
  }

  function handleDragOver(e) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    handleFileSelect(file || null);
  }

  function handleUpload() {
    if (!selectedFile) return;
    startUpload(selectedFile, label);
    setSelectedFile(null);
    setLabel('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

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

  return (
    <div style={{ marginTop: '20px' }}>
      {/* Upload Box */}
      <div className={s.uploadCard}>
        <p className={s.uploadCardTitle}>Upload New Manual Document</p>
        <div
          className={`${s.dropZone} ${isDragOver ? s.dropZoneActive : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          aria-label="Click or drag file here to select"
          id="upload-drop-zone"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={SUPPORTED_ACCEPT}
            className={s.fileInput}
            onChange={handleInputChange}
            onClick={(e) => e.stopPropagation()}
            id="file-input"
            tabIndex={-1}
            aria-hidden="true"
          />
          <UploadCloudIcon />
          {selectedFile ? (
            <span className={s.selectedFile}>
              <FileIcon />
              {selectedFile.name}
            </span>
          ) : (
            <>
              <span className={s.dropZoneText}>Click or drag file here</span>
              <span className={s.dropZoneTextSub}>Supports multiple document formats</span>
            </>
          )}
        </div>

        <p className={s.formatsHint}>
          <strong>Supported formats:</strong> {SUPPORTED_LABEL}
        </p>

        <div className={s.formRow}>
          <label htmlFor="label-input" className={s.formLabel}>
            Label (optional) - e.g. division name
          </label>
          <input
            id="label-input"
            type="text"
            className={s.textInput}
            placeholder="Example: Commercial - Vessel Service"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>

        <button
          className={s.uploadBtn}
          onClick={handleUpload}
          disabled={!selectedFile}
          id="upload-btn"
        >
          Upload &amp; Index
        </button>

        <p className={s.uploadNote}>
          Upload status is shown in the top bar. You can navigate away while the upload is in progress.
        </p>
      </div>

      {/* Table Section */}
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
    </div>
  );
}
