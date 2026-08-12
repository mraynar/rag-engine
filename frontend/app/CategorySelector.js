// frontend/app/CategorySelector.js
'use client';

import { useState, useRef, useEffect } from 'react';
import { useCategory } from './CategoryContext';

// ---- Inline icons ----
function ChevronDownIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function FolderIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function FileTextIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function SettingsIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function WarningDotIcon() {
  return (
    <span style={{
      width: '6px',
      height: '6px',
      borderRadius: '50%',
      backgroundColor: '#E53E3E',
      display: 'inline-block',
      marginLeft: '6px',
      flexShrink: 0
    }} title="Unsynced" />
  );
}

export default function CategorySelector() {
  const {
    selectedCategory,
    setSelectedCategory,
    categories,
    loadingCategories,
    documents,
    setIsDataModalOpen
  } = useCategory();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (categoryName) => {
    setSelectedCategory(categoryName);
    setIsOpen(false);
  };

  const handleManageDataClick = () => {
    setIsDataModalOpen(true);
    setIsOpen(false);
  };

  const selectedSource = categories.find(c => c.category_name === selectedCategory);
  const needsSync = selectedSource && selectedSource.sync_status === 'never_synced';
  const activeDocs = documents.filter(doc => doc.is_active);

  return (
    <div className="category-selector-container" ref={dropdownRef}>
      <button
        className="category-selector-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="category-selector-label">Data Source:</span>
        <span className="category-selector-value">
          {selectedCategory}
          {needsSync && <WarningDotIcon />}
        </span>
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <div className="category-selector-dropdown" role="listbox">
          <div
            className={`category-selector-item ${selectedCategory === 'Semua Data' ? 'selected' : ''}`}
            role="option"
            aria-selected={selectedCategory === 'Semua Data'}
            onClick={() => handleSelect('Semua Data')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FolderIcon size={14} />
              <span>All Data (Default)</span>
            </div>
          </div>
          
          <div className="category-section-header">OneDrive Categories</div>
          {categories.map((cat) => {
            const isUnsynced = cat.sync_status === 'never_synced';
            return (
              <div
                key={cat.id}
                className={`category-selector-item ${selectedCategory === cat.category_name ? 'selected' : ''}`}
                role="option"
                aria-selected={selectedCategory === cat.category_name}
                onClick={() => handleSelect(cat.category_name)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                  <FolderIcon size={14} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                    {cat.category_name}
                  </span>
                </div>
                {isUnsynced && <span className="category-selector-warning-badge">Unsynced</span>}
              </div>
            );
          })}
          {categories.length === 0 && !loadingCategories && (
            <div className="category-selector-empty">No OneDrive categories found</div>
          )}

          <div className="category-section-header">Manual Documents (Active)</div>
          {activeDocs.map((doc) => {
            return (
              <div
                key={doc.filename}
                className={`category-selector-item ${selectedCategory === doc.filename ? 'selected' : ''}`}
                role="option"
                aria-selected={selectedCategory === doc.filename}
                onClick={() => handleSelect(doc.filename)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                  <FileTextIcon size={14} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }} title={doc.filename}>
                    {doc.filename}
                  </span>
                </div>
              </div>
            );
          })}
          {activeDocs.length === 0 && (
            <div className="category-selector-empty">No active manual documents</div>
          )}

          <hr className="category-selector-divider" />
          <div
            className="category-selector-manage-btn"
            onClick={handleManageDataClick}
            role="button"
          >
            <SettingsIcon size={14} />
            <span>Manage Data Sources</span>
          </div>
        </div>
      )}

      <style jsx>{`
        .category-selector-container {
          position: relative;
          display: inline-block;
          font-family: 'Inter', sans-serif;
          z-index: 1000;
        }

        .category-selector-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 6px;
          padding: 8px 12px;
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--color-text);
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .category-selector-btn:hover {
          border-color: var(--color-accent);
          background: var(--color-bg);
        }

        .category-selector-label {
          color: var(--color-muted);
          font-weight: 400;
        }

        .category-selector-value {
          display: flex;
          align-items: center;
          color: var(--color-navy);
          font-weight: 600;
        }

        .category-selector-dropdown {
          position: absolute;
          top: calc(100% + 4px);
          right: 0;
          min-width: 280px;
          max-width: 320px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 8px;
          box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
          padding: 6px;
          margin: 0;
          max-height: 380px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .category-section-header {
          font-size: 0.7rem;
          font-weight: 700;
          color: var(--color-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 8px 12px 4px 12px;
          border-top: 1px solid #EDF2F7;
          margin-top: 4px;
        }

        .category-section-header:first-of-type {
          border-top: none;
          margin-top: 0;
        }

        .category-selector-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          font-size: 0.85rem;
          color: var(--color-text);
          border-radius: 6px;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .category-selector-item:hover {
          background: var(--color-bg);
          color: var(--color-navy);
        }

        .category-selector-item.selected {
          background: var(--color-accent-light);
          color: var(--color-accent);
          font-weight: 600;
        }

        .category-selector-warning-badge {
          font-size: 0.7rem;
          background-color: #FEFCBF;
          color: #B7791F;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 500;
          flex-shrink: 0;
        }

        .category-selector-empty {
          padding: 6px 12px;
          font-size: 0.8rem;
          color: var(--color-muted);
          font-style: italic;
        }

        .category-selector-divider {
          border: none;
          border-top: 1px solid var(--color-border);
          margin: 6px 0;
        }

        .category-selector-manage-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 10px;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 700;
          color: var(--color-accent);
          background-color: var(--color-accent-light);
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .category-selector-manage-btn:hover {
          background-color: var(--color-navy);
          color: #fff;
        }
      `}</style>
    </div>
  );
}
