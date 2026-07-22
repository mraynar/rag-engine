// frontend/app/config/page.js
// Config management page — grouped table UI.
// API: GET /config (list), POST /config (create), PUT /config/{key} (update),
//      PATCH /config/{key}/activate (set active), DELETE /config/{key} (remove)
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import s from './config.module.css';
import {
  LockIcon, EyeIcon, EyeOffIcon, PencilIcon, TrashIcon,
  PlusIcon, CheckIcon, CheckCircleIcon, AlertCircleIcon,
  XIcon, SpinnerIcon, RefreshIcon,
} from '../icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// ─────────────────────────────────────────────
// Toast system (floating, bottom-right stack)
// ─────────────────────────────────────────────

let _toastId = 0;

function useToasts() {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = 'success') => {
    const id = ++_toastId;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return { toasts, push, dismiss };
}

function ToastStack({ toasts, dismiss }) {
  if (!toasts.length) return null;
  return (
    <div className={s.toastStack} aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`${s.toast} ${t.type === 'success' ? s.toastSuccess : s.toastError}`} role="alert">
          <span className={s.toastIcon}>
            {t.type === 'success' ? <CheckCircleIcon size={15} /> : <AlertCircleIcon size={15} />}
          </span>
          <span className={s.toastText}>{t.message}</span>
          <button className={s.toastClose} onClick={() => dismiss(t.id)} aria-label="Tutup">
            <XIcon size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Delete confirm overlay
// ─────────────────────────────────────────────

function ConfirmDelete({ entry, onConfirm, onCancel, loading }) {
  return (
    <div className={s.confirmOverlay} role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className={s.confirmBox}>
        <p className={s.confirmTitle} id="confirm-title">Hapus Entri Konfigurasi?</p>
        <p className={s.confirmDesc}>
          Anda akan menghapus <strong>{entry.description || entry.key}</strong>.
          {' '}Tindakan ini tidak bisa dibatalkan.
          {entry.is_active && (
            <> Karena ini entri aktif, sistem akan otomatis mengaktifkan kandidat lain.</>
          )}
        </p>
        <div className={s.confirmActions}>
          <button className={s.cancelBtn} onClick={onCancel} disabled={loading}>
            Batal
          </button>
          <button
            className={s.confirmDeleteBtn}
            onClick={onConfirm}
            disabled={loading}
            id={`confirm-delete-${entry.key}`}
          >
            {loading
              ? <SpinnerIcon size={14} className={s.spinIcon} />
              : <TrashIcon size={14} />
            }
            Hapus
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Add-candidate inline form (shown per group)
// ─────────────────────────────────────────────

function AddCandidateForm({ group, onSaved, onCancel }) {
  const [description, setDescription] = useState('');
  const [value, setValue] = useState('');
  const [isSecret, setIsSecret] = useState(false);
  const [loading, setLoading] = useState(false);
  const descRef = useRef(null);

  // Focus description field on mount
  useEffect(() => { descRef.current?.focus(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!description.trim() || !value.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group, description: description.trim(), value: value.trim(), is_secret: isSecret }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      onSaved(data.message);
    } catch (err) {
      onSaved(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <tr className={s.addFormRow}>
      <td colSpan={5} className={s.addFormCell}>
        <form className={s.addForm} onSubmit={handleSubmit}>
          <input
            ref={descRef}
            className={s.addInput}
            placeholder="Deskripsi (contoh: Gemini 2.0 Flash)"
            value={description}
            onChange={e => setDescription(e.target.value)}
            required
            aria-label="Deskripsi kandidat baru"
          />
          <input
            className={s.addInput}
            placeholder="Nilai (contoh: gemini-2.0-flash)"
            value={value}
            onChange={e => setValue(e.target.value)}
            type={isSecret ? 'password' : 'text'}
            required
            aria-label="Nilai kandidat baru"
          />
          <label className={s.addSecretToggle}>
            <input
              type="checkbox"
              checked={isSecret}
              onChange={e => setIsSecret(e.target.checked)}
            />
            Rahasia
          </label>
          <button
            type="submit"
            className={s.saveBtn}
            disabled={loading || !description.trim() || !value.trim()}
            id={`add-candidate-save-${group}`}
          >
            {loading ? <SpinnerIcon size={13} className={s.spinIcon} /> : <PlusIcon size={13} />}
            Tambah
          </button>
          <button type="button" className={s.cancelBtn} onClick={onCancel} disabled={loading}>
            Batal
          </button>
        </form>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────
// Single entry row
// ─────────────────────────────────────────────

function EntryRow({ entry, isOnlyInGroup, onActivate, onUpdate, onDelete, toast }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editDesc, setEditDesc] = useState(entry.description);
  const [editValue, setEditValue] = useState(''); // empty = keep existing
  const [showSecret, setShowSecret] = useState(false);
  const [revealedValue, setRevealedValue] = useState(null);
  const [revealing, setRevealing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);
  const editDescRef = useRef(null);

  // Reset states when entry changes from outside (e.g. reload or edit success)
  useEffect(() => {
    setEditDesc(entry.description);
    setEditValue('');
    setShowSecret(false);
    setRevealedValue(null);
  }, [entry]);

  // Focus description input when entering edit mode
  useEffect(() => {
    if (isEditing) editDescRef.current?.focus();
  }, [isEditing]);

  async function handleSave() {
    setSaving(true);
    try {
      const payload = {};
      if (editDesc.trim() !== entry.description) payload.description = editDesc.trim();
      if (editValue.trim()) payload.value = editValue.trim();
      if (Object.keys(payload).length === 0) { setIsEditing(false); return; }

      const res = await fetch(`${API_URL}/config/${entry.key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setIsEditing(false);
      onUpdate(data.message);
    } catch (err) {
      onUpdate(err.message, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function handleActivate() {
    setActivating(true);
    try {
      const res = await fetch(`${API_URL}/config/${entry.key}/activate`, { method: 'PATCH' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      onActivate(data.message);
    } catch (err) {
      onActivate(err.message, 'error');
    } finally {
      setActivating(false);
    }
  }

  async function handleToggleSecret() {
    if (showSecret) {
      setShowSecret(false);
      return;
    }

    if (revealedValue !== null) {
      setShowSecret(true);
      return;
    }

    setRevealing(true);
    try {
      const res = await fetch(`${API_URL}/config/${entry.key}/reveal`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Gagal memuat nilai (${res.status})`);
      }
      const data = await res.json();
      setRevealedValue(data.value);
      setShowSecret(true);
    } catch (err) {
      toast.push(err.message || 'Gagal menampilkan nilai rahasia.', 'error');
    } finally {
      setRevealing(false);
    }
  }

  // Display value: for secret fields, show bullets unless explicitly toggled and fetched
  const displayValue = entry.is_secret
    ? (showSecret && revealedValue !== null ? revealedValue : '••••••••')
    : entry.value;


  const trClass = `${s.tr} ${entry.is_active ? s.trActive : ''} ${isEditing ? s.trEditing : ''}`;

  if (isEditing) {
    return (
      <tr className={trClass}>
        {/* Key */}
        <td className={s.editCell}>
          <div className={s.keyCell}>
            <code className={s.keyCode}>{entry.key}</code>
          </div>
        </td>
        {/* Description (editable) */}
        <td className={s.editCell}>
          <input
            ref={editDescRef}
            className={s.editInput}
            value={editDesc}
            onChange={e => setEditDesc(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
            aria-label="Edit deskripsi"
          />
        </td>
        {/* Value (editable — blank = keep) */}
        <td className={s.editCell}>
          <input
            className={s.editInput}
            value={editValue}
            onChange={e => setEditValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
            type={entry.is_secret ? 'password' : 'text'}
            placeholder={entry.is_secret ? 'Kosongkan = tidak berubah' : entry.value}
            aria-label="Edit nilai"
          />
        </td>
        {/* Active — kept as-is */}
        <td className={`${s.td} ${s.tdCenter}`}>
          {entry.is_active
            ? <span className={s.activePill}><CheckIcon size={10} /> Aktif</span>
            : <span style={{ color: 'var(--color-muted)', fontSize: '0.75rem' }}>—</span>
          }
        </td>
        {/* Actions */}
        <td className={`${s.td} ${s.tdRight}`}>
          <div className={s.actionsCell}>
            <button
              className={`${s.iconBtn} ${s.iconBtnSave}`}
              onClick={handleSave}
              disabled={saving}
              title="Simpan perubahan"
              aria-label="Simpan perubahan"
            >
              {saving ? <SpinnerIcon size={14} className={s.spinIcon} /> : <CheckIcon size={14} />}
            </button>
            <button
              className={s.iconBtn}
              onClick={() => setIsEditing(false)}
              disabled={saving}
              title="Batal"
              aria-label="Batal edit"
            >
              <XIcon size={14} />
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr className={trClass}>
      {/* Key */}
      <td className={s.td}>
        <div className={s.keyCell}>
          <code className={s.keyCode}>{entry.key}</code>
          {entry.is_secret && (
            <span className={s.secretBadge} title="Nilai rahasia">
              <LockIcon size={11} />
            </span>
          )}
        </div>
      </td>

      {/* Description */}
      <td className={s.td} style={{ color: 'var(--color-text-light)' }}>
        {entry.description}
      </td>

      {/* Value */}
      <td className={s.td}>
        <div className={s.valueCell}>
          <span className={`${s.valueText} ${entry.is_secret && !showSecret ? s.valueTextSecret : ''}`}>
            {displayValue}
          </span>
          {entry.is_secret && (
            <button
              className={s.eyeBtn}
              onClick={handleToggleSecret}
              disabled={revealing}
              title={showSecret ? 'Sembunyikan' : 'Tampilkan'}
              aria-label={showSecret ? 'Sembunyikan nilai' : 'Tampilkan nilai'}
            >
              {revealing ? (
                <SpinnerIcon size={14} className={s.spinIcon} />
              ) : showSecret ? (
                <EyeOffIcon size={14} />
              ) : (
                <EyeIcon size={14} />
              )}
            </button>
          )}
        </div>
      </td>

      {/* Active */}
      <td className={`${s.td} ${s.tdCenter}`}>
        {entry.is_active
          ? (
            <span className={s.activePill}>
              <CheckIcon size={10} /> Aktif
            </span>
          ) : (
            <button
              className={s.activateBtn}
              onClick={handleActivate}
              disabled={activating}
              id={`activate-btn-${entry.key}`}
              aria-label={`Aktifkan ${entry.key}`}
            >
              {activating ? <SpinnerIcon size={12} className={s.spinIcon} /> : 'Aktifkan'}
            </button>
          )
        }
      </td>

      {/* Actions */}
      <td className={`${s.td} ${s.tdRight}`}>
        <div className={s.actionsCell}>
          <button
            className={s.iconBtn}
            onClick={() => setIsEditing(true)}
            title="Edit entri ini"
            aria-label={`Edit ${entry.key}`}
            id={`edit-btn-${entry.key}`}
          >
            <PencilIcon size={14} />
          </button>
          <button
            className={`${s.iconBtn} ${s.iconBtnDanger}`}
            onClick={() => onDelete(entry)}
            disabled={isOnlyInGroup}
            title={isOnlyInGroup
              ? 'Tidak bisa dihapus — ini satu-satunya opsi di kategori ini'
              : 'Hapus entri ini'}
            aria-label={`Hapus ${entry.key}`}
            id={`delete-btn-${entry.key}`}
          >
            <TrashIcon size={14} />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────
// Group section (one per config group)
// ─────────────────────────────────────────────

function GroupSection({ groupName, entries, onRefresh, toast }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null); // entry to confirm delete
  const [deleting, setDeleting] = useState(false);

  function handleAddSaved(message, type = 'success') {
    setShowAddForm(false);
    toast.push(message, type);
    if (type !== 'error') onRefresh();
  }

  function handleEntryUpdate(message, type = 'success') {
    toast.push(message, type);
    if (type !== 'error') onRefresh();
  }

  function handleEntryActivate(message, type = 'success') {
    toast.push(message, type);
    if (type !== 'error') onRefresh();
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_URL}/config/${deleteTarget.key}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      toast.push(data.message, 'success');
      setDeleteTarget(null);
      onRefresh();
    } catch (err) {
      toast.push(err.message, 'error');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className={s.groupSection}>
        {/* Group header */}
        <div className={s.groupHeader}>
          <div>
            <div className={s.groupName}>{groupName}</div>
            <div className={s.groupMeta}>{entries.length} kandidat</div>
          </div>
          <button
            className={s.addBtn}
            onClick={() => setShowAddForm(v => !v)}
            id={`add-btn-${groupName}`}
            aria-expanded={showAddForm}
          >
            <PlusIcon size={12} />
            Tambah Kandidat
          </button>
        </div>

        {/* Table */}
        <table className={s.table} aria-label={`Konfigurasi grup ${groupName}`}>
          <thead>
            <tr>
              <th className={s.th} style={{ width: '18%' }}>Key</th>
              <th className={s.th} style={{ width: '30%' }}>Deskripsi</th>
              <th className={s.th} style={{ width: '28%' }}>Nilai</th>
              <th className={`${s.th} ${s.thCenter}`} style={{ width: '12%' }}>Status</th>
              <th className={`${s.th} ${s.thRight}`}  style={{ width: '12%' }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(entry => (
              <EntryRow
                key={entry.key}
                entry={entry}
                isOnlyInGroup={entries.length === 1}
                onActivate={handleEntryActivate}
                onUpdate={handleEntryUpdate}
                onDelete={(e) => setDeleteTarget(e)}
                toast={toast}
              />
            ))}
            {showAddForm && (
              <AddCandidateForm
                group={groupName}
                onSaved={handleAddSaved}
                onCancel={() => setShowAddForm(false)}
              />
            )}
          </tbody>
        </table>
      </div>

      {/* Delete confirmation overlay */}
      {deleteTarget && (
        <ConfirmDelete
          entry={deleteTarget}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </>
  );
}

// ─────────────────────────────────────────────
// Skeleton loader
// ─────────────────────────────────────────────

function SkeletonLoader() {
  return (
    <div className={s.skeletonWrap} aria-hidden="true">
      {[1, 2, 3].map(i => (
        <div key={i} className={s.skeletonGroup}>
          <div className={s.skeletonGroupHeader} />
          {[1, 2].map(j => <div key={j} className={s.skeletonRow} />)}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Config Page
// ─────────────────────────────────────────────

export default function ConfigPage() {
  const [entries, setEntries] = useState(null); // null = loading
  const [fetchError, setFetchError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const toast = useToasts();

  // Group entries by their "group" field, preserving order of first appearance
  const groupedEntries = entries
    ? entries.reduce((acc, entry) => {
        if (!acc[entry.group]) acc[entry.group] = [];
        acc[entry.group].push(entry);
        return acc;
      }, {})
    : {};

  const groupNames = Object.keys(groupedEntries);

  async function loadConfig() {
    setFetchError(null);
    setRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/config`);
      if (!res.ok) throw new Error(`Server error (${res.status})`);
      const data = await res.json();
      setEntries(data);
    } catch (err) {
      setFetchError(err.message || 'Gagal memuat konfigurasi.');
      setEntries([]); // stop skeleton
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { loadConfig(); }, []);

  const isLoading = entries === null;

  return (
    <div className={s.page}>
      {/* ---- Page header ---- */}
      <div className={s.pageHeader}>
        <div className={s.pageHeaderInner}>
          <h1 className={s.pageTitle}>Konfigurasi Sistem</h1>
          <p className={s.pageSubtitle}>
            Kelola kandidat dan nilai aktif untuk setiap parameter RAG Engine.
          </p>
        </div>
        <button
          id="config-refresh-btn"
          className={s.refreshBtn}
          onClick={loadConfig}
          disabled={isLoading || refreshing}
          aria-label="Muat ulang konfigurasi"
        >
          <RefreshIcon size={13} className={refreshing ? s.spinIcon : undefined} />
          Muat Ulang
        </button>
      </div>

      {/* ---- Fetch error ---- */}
      {fetchError && (
        <div className={s.pageError} role="alert">
          <AlertCircleIcon size={18} />
          <div className={s.pageErrorBody}>
            <strong>Gagal memuat konfigurasi</strong>
            <p>{fetchError}</p>
          </div>
          <button className={s.pageErrorRetry} onClick={loadConfig}>Coba Lagi</button>
        </div>
      )}

      {/* ---- Loading skeleton ---- */}
      {isLoading && <SkeletonLoader />}

      {/* ---- Groups ---- */}
      {!isLoading && (
        <div className={s.groupsList}>
          {groupNames.length === 0 && !fetchError && (
            <p style={{ textAlign: 'center', color: 'var(--color-muted)', padding: '3rem' }}>
              Tidak ada konfigurasi ditemukan.
            </p>
          )}
          {groupNames.map(name => (
            <GroupSection
              key={name}
              groupName={name}
              entries={groupedEntries[name]}
              onRefresh={loadConfig}
              toast={toast}
            />
          ))}
        </div>
      )}

      {/* ---- Floating toast stack ---- */}
      <ToastStack toasts={toast.toasts} dismiss={toast.dismiss} />
    </div>
  );
}
