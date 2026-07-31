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
    }} title="Belum disinkronkan" />
  );
}

export default function CategorySelector() {
  const { selectedCategory, setSelectedCategory, categories, loadingCategories } = useCategory();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
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

  const selectedSource = categories.find(c => c.category_name === selectedCategory);
  const needsSync = selectedSource && selectedSource.sync_status === 'never_synced';

  return (
    <div className="category-selector-container" ref={dropdownRef}>
      <button
        className="category-selector-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="category-selector-label">Sumber Data:</span>
        <span className="category-selector-value">
          {selectedCategory}
          {needsSync && <WarningDotIcon />}
        </span>
        <ChevronDownIcon />
      </button>

      {isOpen && (
        <ul className="category-selector-dropdown" role="listbox">
          <li
            className={`category-selector-item ${selectedCategory === 'Semua Data' ? 'selected' : ''}`}
            role="option"
            aria-selected={selectedCategory === 'Semua Data'}
            onClick={() => handleSelect('Semua Data')}
          >
            Semua Data (Upload Manual)
          </li>
          
          {categories.map((cat) => {
            const isUnsynced = cat.sync_status === 'never_synced';
            return (
              <li
                key={cat.id}
                className={`category-selector-item ${selectedCategory === cat.category_name ? 'selected' : ''}`}
                role="option"
                aria-selected={selectedCategory === cat.category_name}
                onClick={() => handleSelect(cat.category_name)}
              >
                {cat.category_name}
                {isUnsynced && <span className="category-selector-warning-badge">Belum Sync</span>}
              </li>
            );
          })}
          
          {categories.length === 0 && !loadingCategories && (
            <li className="category-selector-empty">Belum ada kategori OneDrive</li>
          )}
        </ul>
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
          min-width: 260px;
          background: var(--color-surface);
          border: 1px solid var(--color-border);
          border-radius: 8px;
          box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
          padding: 6px;
          margin: 0;
          list-style: none;
          max-height: 300px;
          overflow-y: auto;
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
        }

        .category-selector-empty {
          padding: 12px;
          font-size: 0.8rem;
          color: var(--color-muted);
          text-align: center;
        }
      `}</style>
    </div>
  );
}
