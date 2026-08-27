'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import s from './config/config.module.css';
import {
  LockIcon, EyeIcon, EyeOffIcon, PencilIcon, TrashIcon,
  PlusIcon, CheckIcon, CheckCircleIcon, AlertCircleIcon,
  XIcon, SpinnerIcon, RefreshIcon, SendIcon, ChatIcon, SunIcon
} from './icons';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

let _toastId = 0;


function ConfirmDelete({ entry, onConfirm, onCancel, loading }) {
  return (
    <div className={s.confirmOverlay} role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className={s.confirmBox}>
        <p className={s.confirmTitle} id="confirm-title">Delete Configuration Entry?</p>
        <p className={s.confirmDesc}>
          You are about to delete <strong>{entry.description || entry.key}</strong>.
          {' '}This action cannot be undone.
          {entry.is_active && (
            <> Since this is the active entry, the system will automatically activate another candidate.</>
          )}
        </p>
        <div className={s.confirmActions}>
          <button className={s.cancelBtn} onClick={onCancel} disabled={loading}>
            Cancel
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
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Add candidate form (handles standard & azure)
// ─────────────────────────────────────────────
function AddCandidateForm({ group, onSaved, onCancel }) {
  // Standard fields
  const [description, setDescription] = useState('');
  const [value, setValue] = useState('');
  const [isSecret, setIsSecret] = useState(group === 'gemini_api_key' || group === 'groq_api_key');
  
  // Azure fields
  const [azureTenant, setAzureTenant] = useState('');
  const [azureClient, setAzureClient] = useState('');
  const [azureSecret, setAzureSecret] = useState('');

  const [loading, setLoading] = useState(false);
  const descRef = useRef(null);

  useEffect(() => { descRef.current?.focus(); }, []);

  const isAzure = group === 'azure_graph';

  async function handleSubmit(e) {
    e.preventDefault();
    if (!description.trim()) return;

    let finalValue = value.trim();
    if (isAzure) {
      if (!azureTenant.trim() || !azureClient.trim() || !azureSecret.trim()) return;
      finalValue = JSON.stringify({
        tenant_id: azureTenant.trim(),
        client_id: azureClient.trim(),
        client_secret: azureSecret.trim()
      });
    } else {
      if (!finalValue) return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group,
          description: description.trim(),
          value: finalValue,
          is_secret: isAzure ? true : isSecret
        }),
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
      <td colSpan={isAzure ? 7 : 5} className={s.addFormCell}>
        <form className={s.addForm} onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', width: '100%' }}>
            <div style={{ gridColumn: 'span 2' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--color-navy)', marginBottom: '4px', textAlign: 'left' }}>
                Description / Label
              </label>
              <input
                ref={descRef}
                className={s.addInput}
                placeholder={isAzure ? "Example: Azure Prod TPS" : "Example: Main Gemini API Key"}
                value={description}
                onChange={e => setDescription(e.target.value)}
                required
                style={{ width: '100%', boxSizing: 'border-box' }}
              />
            </div>

            {isAzure ? (
              <>
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--color-navy)', marginBottom: '4px', textAlign: 'left' }}>
                    Tenant ID (Directory ID)
                  </label>
                  <input
                    className={s.addInput}
                    placeholder="AZURE_TENANT_ID"
                    value={azureTenant}
                    onChange={e => setAzureTenant(e.target.value)}
                    required
                    style={{ width: '100%', boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--color-navy)', marginBottom: '4px', textAlign: 'left' }}>
                    Client ID (Application ID)
                  </label>
                  <input
                    className={s.addInput}
                    placeholder="AZURE_CLIENT_ID"
                    value={azureClient}
                    onChange={e => setAzureClient(e.target.value)}
                    required
                    style={{ width: '100%', boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--color-navy)', marginBottom: '4px', textAlign: 'left' }}>
                    Client Secret Value
                  </label>
                  <input
                    className={s.addInput}
                    placeholder="AZURE_CLIENT_SECRET"
                    value={azureSecret}
                    onChange={e => setAzureSecret(e.target.value)}
                    type="password"
                    required
                    style={{ width: '100%', boxSizing: 'border-box' }}
                  />
                </div>
              </>
            ) : (
              <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--color-navy)', textAlign: 'left' }}>
                  Parameter Value
                </label>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', width: '100%' }}>
                  <input
                    className={s.addInput}
                    placeholder="Enter parameter value"
                    value={value}
                    onChange={e => setValue(e.target.value)}
                    type={isSecret ? 'password' : 'text'}
                    required
                    style={{ width: '100%', boxSizing: 'border-box', paddingRight: '40px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setIsSecret(!isSecret)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      background: 'none',
                      border: 'none',
                      padding: '4px',
                      cursor: 'pointer',
                      color: 'var(--color-text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    title={isSecret ? "Show Value" : "Hide Value"}
                  >
                    {isSecret ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button type="button" className={s.cancelBtn} onClick={onCancel} disabled={loading}>
              Cancel
            </button>
            <button
              type="submit"
              className={s.saveBtn}
              disabled={loading || !description.trim()}
              id={`add-candidate-save-${group}`}
            >
              {loading ? <SpinnerIcon size={13} className={s.spinIcon} /> : <PlusIcon size={13} />}
              Add
            </button>
          </div>
        </form>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────
// Single Entry Row
// ─────────────────────────────────────────────
function EntryRow({ entry, isOnlyInGroup, onActivate, onUpdate, onDelete, toast }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editDesc, setEditDesc] = useState(entry.description);
  const [editValue, setEditValue] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [revealedValue, setRevealedValue] = useState(null);
  const [revealing, setRevealing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);
  const editDescRef = useRef(null);

  const isAzure = entry.group === 'azure_graph';

  // Custom Azure edit fields
  const [azureTenant, setAzureTenant] = useState('');
  const [azureClient, setAzureClient] = useState('');
  const [azureSecret, setAzureSecret] = useState('');

  useEffect(() => {
    setEditDesc(entry.description);
    setEditValue('');
    setShowSecret(false);
    setRevealedValue(null);
  }, [entry]);

  useEffect(() => {
    if (isEditing) editDescRef.current?.focus();
  }, [isEditing]);

  async function handleSave() {
    setSaving(true);
    try {
      const payload = {};
      if (editDesc.trim() !== entry.description) payload.description = editDesc.trim();
      
      if (isAzure) {
        // Only updates if all are filled or at least some change
        if (azureTenant.trim() || azureClient.trim() || azureSecret.trim()) {
          // If we had revealed it, we can pre-populate the unchanged fields
          let currentCreds = {};
          if (revealedValue) {
            try { currentCreds = JSON.parse(revealedValue); } catch {}
          }
          payload.value = JSON.stringify({
            tenant_id: azureTenant.trim() || currentCreds.tenant_id || '',
            client_id: azureClient.trim() || currentCreds.client_id || '',
            client_secret: azureSecret.trim() || currentCreds.client_secret || ''
          });
        }
      } else {
        if (editValue.trim()) payload.value = editValue.trim();
      }

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
    if (!entry.is_secret) {
      setRevealedValue(entry.value);
      setShowSecret(true);
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
        throw new Error(err.detail || `Failed to load value (${res.status})`);
      }
      const data = await res.json();
      setRevealedValue(data.value);
      setShowSecret(true);
    } catch (err) {
      toast.push(err.message || 'Failed to reveal secret value.', 'error');
    } finally {
      setRevealing(false);
    }
  }

  // Display text formatter
  const displayValue = showSecret ? (revealedValue ?? entry.value) : '••••••••';

  let creds = { tenant_id: '', client_id: '', client_secret: '' };
  if (isAzure) {
    try {
      const rawVal = revealedValue ?? entry.value;
      if (rawVal) {
        creds = JSON.parse(rawVal);
      }
    } catch (e) {}
  }

  const trClass = `${s.tr} ${entry.is_active ? s.trActive : ''} ${isEditing ? s.trEditing : ''}`;

  if (isEditing) {
    return (
      <tr className={trClass}>
        <td className={s.editCell}>
          <div className={s.keyCell}>
            <code className={s.keyCode}>{entry.key}</code>
          </div>
        </td>
        <td className={s.editCell}>
          <input
            ref={editDescRef}
            className={s.editInput}
            value={editDesc}
            onChange={e => setEditDesc(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
            aria-label="Edit description"
          />
        </td>
        {isAzure ? (
          <>
            <td className={s.editCell}>
              <input
                className={s.editInput}
                placeholder="Tenant ID (leave blank = unchanged)"
                value={azureTenant}
                onChange={e => setAzureTenant(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
                style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
              />
            </td>
            <td className={s.editCell}>
              <input
                className={s.editInput}
                placeholder="Client ID (leave blank = unchanged)"
                value={azureClient}
                onChange={e => setAzureClient(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
                style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
              />
            </td>
            <td className={s.editCell}>
              <input
                className={s.editInput}
                placeholder="Client Secret (leave blank = unchanged)"
                value={azureSecret}
                onChange={e => setAzureSecret(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
                type="password"
                style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
              />
            </td>
          </>
        ) : (
          <td className={s.editCell}>
            <input
              className={s.editInput}
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setIsEditing(false); }}
              type="password"
              placeholder="Leave blank = unchanged"
              aria-label="Edit value"
            />
          </td>
        )}
        <td className={`${s.td} ${s.tdCenter}`}>
          {entry.is_active
            ? <span className={s.activePill}><CheckIcon size={10} /> Active</span>
            : <span style={{ color: 'var(--color-muted)', fontSize: '0.75rem' }}>—</span>
          }
        </td>
        <td className={`${s.td} ${s.tdRight}`}>
          <div className={s.actionsCell}>
            <button
              className={`${s.iconBtn} ${s.iconBtnSave}`}
              onClick={handleSave}
              disabled={saving}
              title="Save changes"
              aria-label="Save changes"
            >
              {saving ? <SpinnerIcon size={14} className={s.spinIcon} /> : <CheckIcon size={14} />}
            </button>
            <button
              className={s.iconBtn}
              onClick={() => setIsEditing(false)}
              disabled={saving}
              title="Cancel"
              aria-label="Cancel edit"
            >
              <XIcon size={14} />
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr className={trClass} style={{ borderBottom: '1px solid var(--color-border)' }}>
      <td className={s.td}>
        <div className={s.keyCell}>
          <code className={s.keyCode}>{entry.key}</code>
          {entry.is_secret && (
            <span className={s.secretBadge} title="Secret value">
              <LockIcon size={11} />
            </span>
          )}
        </div>
      </td>
      <td className={s.td} style={{ color: 'var(--color-text-light)' }}>
        {entry.description}
      </td>
      {isAzure ? (
        <>
          <td className={s.td}>
            <code style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text)' }}>
              {showSecret ? creds.tenant_id : '••••••••••••••••'}
            </code>
          </td>
          <td className={s.td}>
            <code style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text)' }}>
              {showSecret ? creds.client_id : '••••••••••••••••'}
            </code>
          </td>
          <td className={s.td}>
            <div className={s.valueCell}>
              <code style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text)' }}>
                {showSecret ? creds.client_secret : '••••••••••••••••'}
              </code>
              <button
                className={s.eyeBtn}
                onClick={handleToggleSecret}
                disabled={revealing}
                title={showSecret ? 'Hide' : 'Show'}
                aria-label={showSecret ? 'Hide value' : 'Show value'}
              >
                {revealing ? (
                  <SpinnerIcon size={14} className={s.spinIcon} />
                ) : showSecret ? (
                  <EyeOffIcon size={14} />
                ) : (
                  <EyeIcon size={14} />
                )}
              </button>
            </div>
          </td>
        </>
      ) : (
        <td className={s.td}>
          <div className={s.valueCell}>
            <span className={`${s.valueText} ${!showSecret ? s.valueTextSecret : ''}`}>
              {displayValue}
            </span>
            <button
              className={s.eyeBtn}
              onClick={handleToggleSecret}
              disabled={revealing}
              title={showSecret ? 'Hide' : 'Show'}
              aria-label={showSecret ? 'Hide value' : 'Show value'}
            >
              {revealing ? (
                <SpinnerIcon size={14} className={s.spinIcon} />
              ) : showSecret ? (
                <EyeOffIcon size={14} />
              ) : (
                <EyeIcon size={14} />
              )}
            </button>
          </div>
        </td>
      )}
      <td className={`${s.td} ${s.tdCenter}`}>
        {entry.is_active
          ? (
            <span className={s.activePill}>
              <CheckIcon size={10} /> Active
            </span>
          ) : (
            <button
              className={s.activateBtn}
              onClick={handleActivate}
              disabled={activating}
              id={`activate-btn-${entry.key}`}
              aria-label={`Activate ${entry.key}`}
            >
              {activating ? <SpinnerIcon size={12} className={s.spinIcon} /> : 'Activate'}
            </button>
          )
        }
      </td>
      <td className={`${s.td} ${s.tdRight}`}>
        <div className={s.actionsCell}>
          <button
            className={s.iconBtn}
            onClick={() => setIsEditing(true)}
            title="Edit this entry"
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
              ? 'Cannot delete — this is the only option in this category'
              : 'Delete this entry'}
            aria-label={`Delete ${entry.key}`}
            id={`delete-btn-${entry.key}`}
          >
            <TrashIcon size={14} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function GroupSection({ groupName, entries, onRefresh, toast }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Group label translation for user friendliness
  const friendlyNames = {
    gemini_api_key: "Gemini API Key",
    embedding_model: "Embedding Model",
    generation_model: "Generation Model (LLM)",
    azure_graph: "Azure / Microsoft Graph API Credentials",
    groq_api_key: "Groq API Key (Narrative Generation)",
    groq_model: "Groq Model"
  };

  const displayName = friendlyNames[groupName] || groupName;

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
        <div className={s.groupHeader}>
          <div>
            <div className={s.groupName}>{displayName}</div>
            <div className={s.groupMeta}>{entries.length} candidate(s)</div>
          </div>
          <button
            className={s.addBtn}
            onClick={() => setShowAddForm(v => !v)}
            id={`add-btn-${groupName}`}
            aria-expanded={showAddForm}
          >
            <PlusIcon size={12} />
            Add Candidate
          </button>
        </div>

        <div className={s.tableWrapper}>
          <table className={s.table} aria-label={`Configuration group ${groupName}`}>
            <thead>
              <tr style={{ background: 'var(--color-bg)', borderBottom: '1px solid var(--color-border)' }}>
                {groupName === 'azure_graph' ? (
                  <>
                    <th className={s.th} style={{ width: '15%' }}>Key</th>
                    <th className={s.th} style={{ width: '15%' }}>Description</th>
                    <th className={s.th} style={{ width: '20%' }}>Tenant ID</th>
                    <th className={s.th} style={{ width: '20%' }}>Client ID</th>
                    <th className={s.th} style={{ width: '15%' }}>Secret Key</th>
                    <th className={`${s.th} ${s.thCenter}`} style={{ width: '8%' }}>Status</th>
                    <th className={`${s.th} ${s.thRight}`}  style={{ width: '7%' }}>Actions</th>
                  </>
                ) : (
                  <>
                    <th className={s.th} style={{ width: '22%' }}>Key</th>
                    <th className={s.th} style={{ width: '28%' }}>Description</th>
                    <th className={s.th} style={{ width: '28%' }}>Value / Credentials</th>
                    <th className={`${s.th} ${s.thCenter}`} style={{ width: '12%' }}>Status</th>
                    <th className={`${s.th} ${s.thRight}`}  style={{ width: '10%' }}>Actions</th>
                  </>
                )}
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
      </div>

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

function SkeletonLoader() {
  return (
    <div className={s.skeletonWrap} aria-hidden="true">
      {[1, 2].map(i => (
        <div key={i} className={s.skeletonGroup}>
          <div className={s.skeletonGroupHeader} />
          {[1, 2].map(j => <div key={j} className={s.skeletonRow} />)}
        </div>
      ))}
    </div>
  );
}

export default function ConfigManager() {
  const [entries, setEntries] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [toasts, setToasts] = useState([]);
  
  const toast = {
    push: useCallback((message, type = 'success') => {
      const id = ++_toastId;
      setToasts(prev => [...prev, { id, message, type }]);
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
    }, []),
    dismiss: useCallback((id) => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, []),
  };

  const groupedEntries = entries
    ? entries.reduce((acc, entry) => {
        if (!acc[entry.group]) acc[entry.group] = [];
        acc[entry.group].push(entry);
        return acc;
      }, {})
    : {};

  // Force groups order: Gemini key, embedding model, generation model, Groq key, Groq model, azure graph
  const orderedGroups = ['gemini_api_key', 'embedding_model', 'generation_model', 'groq_api_key', 'groq_model', 'azure_graph'];
  const groupNames = Object.keys(groupedEntries);
  const displayGroups = orderedGroups.filter(name => groupNames.includes(name))
    .concat(groupNames.filter(name => !orderedGroups.includes(name)));

  async function loadConfig() {
    setFetchError(null);
    setRefreshing(true);
    try {
      const res = await fetch(`${API_URL}/config`);
      if (!res.ok) throw new Error(`Server error (${res.status})`);
      const data = await res.json();
      setEntries(data);
    } catch (err) {
      setFetchError(err.message || 'Failed to load configuration.');
      setEntries([]);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { loadConfig(); }, []);

  const isLoading = entries === null;

  return (
    <div style={{ marginTop: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--color-navy)' }}>Credential & Model Governance</h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--color-muted)' }}>
            Manage Gemini API Keys, embedding/generation models, and Microsoft Graph API credentials.
          </p>
        </div>
        <button
          className={s.refreshBtn}
          onClick={loadConfig}
          disabled={isLoading || refreshing}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#fff',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '0.8rem',
            cursor: 'pointer',
          }}
        >
          <RefreshIcon size={12} className={refreshing ? s.spinIcon : undefined} />
          Reload
        </button>
      </div>

      {fetchError && (
        <div className={s.pageError} role="alert" style={{ marginBottom: '16px' }}>
          <AlertCircleIcon size={18} />
          <div className={s.pageErrorBody}>
            <strong>Failed to load configuration</strong>
            <p>{fetchError}</p>
          </div>
          <button className={s.pageErrorRetry} onClick={loadConfig}>Retry</button>
        </div>
      )}

      {isLoading && <SkeletonLoader />}

      {!isLoading && (
        <div className={s.groupsList} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {displayGroups.length === 0 && !fetchError && (
            <p style={{ textAlign: 'center', color: 'var(--color-muted)', padding: '3rem' }}>
              No configurations found.
            </p>
          )}
          {displayGroups.map(name => (
            <GroupSection
              key={name}
              groupName={name}
              entries={groupedEntries[name] || []}
              onRefresh={loadConfig}
              toast={toast}
            />
          ))}
        </div>
      )}



      {/* Toasts */}
      {toasts.length > 0 && (
        <div style={{ position: 'fixed', bottom: '20px', right: '20px', display: 'flex', flexDirection: 'column', gap: '8px', zIndex: 1100 }}>
          {toasts.map(t => (
            <div key={t.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 16px',
              borderRadius: '6px',
              background: '#fff',
              border: `1px solid ${t.type === 'success' ? '#C6F6D5' : '#FED7D7'}`,
              boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
              fontSize: '0.8rem',
              color: t.type === 'success' ? '#22543D' : '#742A2A',
            }}>
              {t.type === 'success' ? <CheckCircleIcon size={14} /> : <AlertCircleIcon size={14} />}
              <span>{t.message}</span>
              <button onClick={() => toast.dismiss(t.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--color-muted)' }}>
                <XIcon size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
