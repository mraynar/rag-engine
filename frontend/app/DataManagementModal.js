'use client';

import { useState } from 'react';
import { useCategory } from './CategoryContext';
import OneDriveManager from './OneDriveManager';
import DocumentManager from './DocumentManager';
import AccessTokenManager from './AccessTokenManager';
import { XIcon, TrashIcon } from './icons';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export default function DataManagementModal() {
  const { isDataModalOpen, setIsDataModalOpen } = useCategory();
  const [activeSubTab, setActiveSubTab] = useState('onedrive');
  const [resetting, setResetting] = useState(false);

  async function handleResetData() {
    if (!window.confirm("WARNING: Are you sure you want to delete all application data (Categories, Documents, Chats, Vector Index)? This action is permanent.")) return;
    
    setResetting(true);
    try {
      const res = await fetch(`${API_BASE}/config/reset`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }
      const data = await res.json();
      window.alert(data.message || "Reset completed successfully.");
      window.location.reload();
    } catch (err) {
      window.alert(err.message || 'Failed to reset data.');
    } finally {
      setResetting(false);
    }
  }

  if (!isDataModalOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-navy)', fontWeight: '700' }}>
              Data Source Management
            </h3>
            <p className="modal-desc">
              Manage online data synchronization (OneDrive, Google Drive, Google Sheets) or upload manual documents.
            </p>
          </div>
          
          <button
            onClick={() => setIsDataModalOpen(false)}
            className="modal-close-btn"
            title="Close dialog"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Modal Tabs */}
        <div className="modal-tabs">
          <button
            onClick={() => setActiveSubTab('onedrive')}
            className={`modal-tab-btn ${activeSubTab === 'onedrive' ? 'active' : ''}`}
          >
            Cloud Data Sources
          </button>

          <button
            onClick={() => setActiveSubTab('manual')}
            className={`modal-tab-btn ${activeSubTab === 'manual' ? 'active' : ''}`}
          >
            Manual Documents
          </button>

          <button
            onClick={() => setActiveSubTab('tokens')}
            className={`modal-tab-btn ${activeSubTab === 'tokens' ? 'active' : ''}`}
          >
            Access Tokens
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {activeSubTab === 'onedrive' && <OneDriveManager />}
          {activeSubTab === 'manual' && <DocumentManager />}
          {activeSubTab === 'tokens' && <AccessTokenManager />}

          {/* Danger Zone */}
          <div className="danger-zone">
            <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#C53030', fontWeight: '700' }}>Danger Zone (Reset Data)</h4>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.78rem', color: '#9B2C2C', lineHeight: '1.4' }}>
              Permanently delete all cloud categories, manual documents, chat history, and ChromaDB search indices from the server. This action cannot be undone.
            </p>
            <button
              onClick={handleResetData}
              disabled={resetting}
              className="reset-btn"
            >
              {resetting ? 'Resetting...' : (
                <>
                  <TrashIcon size={14} />
                  Reset All Application Data
                </>
              )}
            </button>
          </div>
        </div>

      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(11, 47, 92, 0.4);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          font-family: 'Inter', sans-serif;
        }

        .modal-box {
          background-color: #fff;
          width: 90%;
          max-width: 950px;
          height: 710px;
          max-height: 85vh;
          border-radius: 12px;
          box-shadow: var(--shadow-lg);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .modal-header {
          padding: 20px 24px;
          border-bottom: 1px solid var(--color-border);
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-shrink: 0;
        }

        .modal-desc {
          margin: 4px 0 0 0;
          font-size: 0.8rem;
          color: var(--color-muted);
        }

        .modal-close-btn {
          padding: 6px;
          border-radius: 50%;
          background-color: #EDF2F7;
          color: var(--color-text-light);
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background-color 0.2s;
        }

        .modal-close-btn:hover {
          background-color: #E2E8F0;
        }

        .modal-tabs {
          padding: 12px 24px 0 24px;
          display: flex;
          gap: 8px;
          background-color: #F8FAFC;
          border-bottom: 1px solid var(--color-border);
          flex-shrink: 0;
        }

        .modal-tab-btn {
          padding: 10px 16px;
          border: none;
          border-bottom: 3px solid transparent;
          background-color: transparent;
          color: var(--color-text-light);
          font-weight: 600;
          font-size: 0.85rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .modal-tab-btn.active {
          border-bottom: 3px solid var(--color-navy);
          color: var(--color-navy);
        }

        .modal-body {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
        }

        .danger-zone {
          margin-top: 40px;
          padding: 16px 20px;
          border: 1px solid #FED7D7;
          border-radius: 8px;
          background-color: #FFF5F5;
        }

        .reset-btn {
          background-color: #E53E3E;
          color: #fff;
          border: none;
          border-radius: 6px;
          padding: 8px 16px;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: background-color 0.2s;
        }

        .reset-btn:hover:not(:disabled) {
          background-color: #C53030;
        }

        @media (max-width: 640px) {
          .modal-box {
            width: 95% !important;
            height: 90vh !important;
            max-height: 90vh !important;
            border-radius: 8px !important;
          }

          .modal-header {
            padding: 14px 16px !important;
          }

          .modal-desc {
            display: none !important;
          }

          .modal-tabs {
            padding: 8px 16px 0 16px !important;
          }

          .modal-tab-btn {
            padding: 8px 10px !important;
            font-size: 0.78rem !important;
          }

          .modal-body {
            padding: 16px !important;
          }

          .danger-zone {
            margin-top: 24px !important;
            padding: 12px 14px !important;
          }
        }
      `}</style>
    </div>
  );
}
