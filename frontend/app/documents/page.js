// frontend/app/documents/page.js
// "Sumber Data" page — upload, manage, and toggle active/inactive documents
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircleIcon, CheckCircleIcon, SpinnerIcon, TrashIcon } from '../icons';
import { useUpload } from '../UploadContext';
import s from './documents.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const SUPPORTED_ACCEPT = '.txt,.csv,.xlsx,.xls,.docx,.pdf,.pptx,.jpg,.jpeg,.png,.webp';
const SUPPORTED_LABEL  = '.txt, .csv, .xlsx, .xls, .docx, .pdf, .pptx, .jpg, .jpeg, .png, .webp';

// ---- Type badge color mapping ----
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

// ---- Upload-area SVG icon ----
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

// ---- File icon ----
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

// ---- Docs empty state icon ----
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

// ---------------------------------------------------------------------------
// Delete confirmation dialog
// ---------------------------------------------------------------------------
function ConfirmDialog({ filename, onConfirm, onCancel, isDeleting }) {
  return (
    <div className={s.confirmOverlay} role="dialog" aria-modal="true"
      aria-labelledby="confirm-title">
      <div className={s.confirmDialog}>
        <p id="confirm-title" className={s.confirmTitle}>Hapus Dokumen</p>
        <p className={s.confirmBody}>
          Apakah kamu yakin ingin menghapus{' '}
          <span className={s.confirmFilename}>{filename}</span>?
          {' '}Semua chunk yang sudah diindeks akan dihapus dari vector store
          dan tidak bisa dipulihkan.
        </p>
        <div className={s.confirmActions}>
          <button className={s.cancelBtn} onClick={onCancel} disabled={isDeleting}>
            Batal
          </button>
          <button className={s.confirmDeleteBtn} onClick={onConfirm} disabled={isDeleting}>
            {isDeleting
              ? <SpinnerIcon size={15} className={s.spin} />
              : 'Hapus'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Document row
// ---------------------------------------------------------------------------
function DocumentRow({ doc, onToggle, onDelete, togglingFilename, deletingFilename }) {
  const isToggling = togglingFilename === doc.filename;
  const date = doc.uploaded_at
    ? new Date(doc.uploaded_at + 'Z').toLocaleDateString('id-ID', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : '—';

  return (
    <tr>
      {/* Filename + label */}
      <td>
        <span className={s.filename} title={doc.filename}>{doc.filename}</span>
        {doc.label && doc.label !== doc.filename && (
          <span className={s.labelText}>{doc.label}</span>
        )}
      </td>

      {/* Type badge */}
      <td><TypeBadge type={doc.file_type} /></td>

      {/* Chunk count */}
      <td><span className={s.chunkCount}>{doc.chunk_count?.toLocaleString('id-ID')}</span></td>

      {/* Upload date */}
      <td><span className={s.dateText}>{date}</span></td>

      {/* Active toggle */}
      <td className={s.toggleCell}>
        <label className={s.toggleLabel}>
          <input
            type="checkbox"
            className={s.toggleCheckbox}
            checked={doc.is_active}
            disabled={isToggling}
            onChange={(e) => onToggle(doc.filename, e.target.checked)}
            id={`toggle-${doc.filename}`}
            aria-label={`Aktifkan ${doc.filename}`}
          />
          {isToggling && <SpinnerIcon size={13} className={s.spin} />}
        </label>
      </td>

      {/* Delete */}
      <td>
        <button
          className={s.deleteBtn}
          onClick={() => onDelete(doc.filename)}
          disabled={!!deletingFilename}
          aria-label={`Hapus ${doc.filename}`}
          title="Hapus dokumen"
          id={`delete-${doc.filename.replace(/\./g, '-')}`}
        >
          <TrashIcon size={15} />
        </button>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function DocumentsPage() {
  const [documents, setDocuments]         = useState([]);
  const [loadingDocs, setLoadingDocs]     = useState(true);
  const [fetchError, setFetchError]       = useState('');

  const [selectedFile, setSelectedFile]   = useState(null);
  const [label, setLabel]                 = useState('');
  const [isDragOver, setIsDragOver]       = useState(false);

  const [togglingFilename, setTogglingFilename] = useState(null);
  const [pendingDelete, setPendingDelete]       = useState(null); // filename
  const [deletingFilename, setDeletingFilename] = useState(null);

  const fileInputRef = useRef(null);

  const { startUpload, registerRefreshCallback, unregisterRefreshCallback } = useUpload();

  // ---- Fetch documents ----
  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true);
    setFetchError('');
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (!res.ok) throw new Error('Gagal memuat daftar dokumen.');
      setDocuments(await res.json());
    } catch (err) {
      setFetchError(err.message);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  // Register refresh callback so the global UploadContext can trigger a list
  // refresh when an upload completes while this page is still mounted.
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

  // ---- Drag & drop ----
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

  // ---- Upload — delegate to global context so it survives navigation ----
  function handleUpload() {
    if (!selectedFile) return;
    startUpload(selectedFile, label);
    setSelectedFile(null);
    setLabel('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  // ---- Toggle active ----
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
        throw new Error(data.detail || 'Gagal mengubah status dokumen.');
      }
      // Optimistic update
      setDocuments(prev =>
        prev.map(d => d.filename === filename ? { ...d, is_active: isActive } : d)
      );
    } catch (err) {
      alert(err.message);
    } finally {
      setTogglingFilename(null);
    }
  }

  // ---- Delete flow ----
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
        throw new Error(data.detail || 'Gagal menghapus dokumen.');
      }
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

  // ---- Render ----
  return (
    <div className={s.page}>
      {/* ---- Header ---- */}
      <div className={s.header}>
        <h1 className={s.title}>Sumber Data</h1>
        <p className={s.subtitle}>
          Kelola dokumen yang diindeks ke vector store. Hanya dokumen aktif yang dicari saat chat.
        </p>
      </div>

      {/* ---- Upload card ---- */}
      <div className={s.uploadCard}>
        <p className={s.uploadCardTitle}>Upload Dokumen Baru</p>

        {/* Drop zone */}
        <div
          className={`${s.dropZone} ${isDragOver ? s.dropZoneActive : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          aria-label="Klik atau seret file ke sini untuk memilih"
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
              <span className={s.dropZoneText}>Klik atau seret file ke sini</span>
              <span className={s.dropZoneTextSub}>Mendukung beberapa format dokumen</span>
            </>
          )}
        </div>

        {/* Supported formats hint */}
        <p className={s.formatsHint}>
          <strong>Format yang didukung:</strong> {SUPPORTED_LABEL}
        </p>

        {/* Label input */}
        <div className={s.formRow}>
          <label htmlFor="label-input" className={s.formLabel}>
            Label (opsional) - misal nama divisi
          </label>
          <input
            id="label-input"
            type="text"
            className={s.textInput}
            placeholder="Contoh: Komersial - Vessel Service"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>

        {/* Upload button */}
        <button
          className={s.uploadBtn}
          onClick={handleUpload}
          disabled={!selectedFile}
          id="upload-btn"
        >
          Upload &amp; Indeks
        </button>

        {/* Feedback — upload notifications now come from the global status pill */}
        <p className={s.uploadNote}>
          Status upload ditampilkan di bar atas. Anda bisa berpindah halaman
          saat upload berlangsung — upload akan tetap berjalan.
        </p>
      </div>

      {/* ---- Document list ---- */}
      <div className={s.listSection}>
        <div className={s.listHeader}>
          <h2 className={s.listTitle}>Dokumen Terdaftar</h2>
          {!loadingDocs && (
            <span className={s.listCount}>
              {documents.length} dokumen
              {documents.filter(d => d.is_active).length > 0 &&
                `, ${documents.filter(d => d.is_active).length} aktif`}
            </span>
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
            <p className={s.emptyTitle}>Belum ada dokumen</p>
            <p className={s.emptyBody}>
              Upload dokumen di atas untuk mulai mengindeks sumber data.
              Chatbot hanya akan menjawab dari dokumen yang aktif.
            </p>
          </div>
        ) : (
          <div className={s.tableWrapper}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th>Dokumen</th>
                  <th>Format</th>
                  <th>Chunk</th>
                  <th>Diupload</th>
                  <th>Aktif</th>
                  <th></th>
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
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ---- Delete confirmation dialog ---- */}
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
