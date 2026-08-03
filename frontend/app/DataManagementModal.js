// frontend/app/DataManagementModal.js
'use client';

import { useState } from 'react';
import { useCategory } from './CategoryContext';
import OneDriveManager from './OneDriveManager';
import DocumentManager from './DocumentManager';
import { XIcon } from './icons';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DataManagementModal() {
  const { isDataModalOpen, setIsDataModalOpen } = useCategory();
  const [activeSubTab, setActiveSubTab] = useState('onedrive'); // 'onedrive' or 'manual'
  const [resetting, setResetting] = useState(false);

  async function handleResetData() {
    if (!window.confirm("PENTING: Apakah Anda benar-benar yakin ingin menghapus seluruh data aplikasi (Kategori, Dokumen, Chat, Index Vektor)? Tindakan ini permanen.")) return;
    
    setResetting(true);
    try {
      const res = await fetch(`${API_BASE}/config/reset`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }
      const data = await res.json();
      window.alert(data.message || "Reset berhasil.");
      window.location.reload();
    } catch (err) {
      window.alert(err.message || 'Gagal me-reset data.');
    } finally {
      setResetting(false);
    }
  }

  if (!isDataModalOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(11, 47, 92, 0.4)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      fontFamily: "'Inter', sans-serif"
    }}>
      {/* Modal Dialog Container */}
      <div style={{
        backgroundColor: '#fff',
        width: '90%',
        maxWidth: '950px',
        height: '710px',
        maxHeight: '85vh',
        borderRadius: '12px',
        boxShadow: 'var(--shadow-lg)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        
        {/* Header Block */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-navy)', fontWeight: '700' }}>
              Manajemen Sumber Data
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: 'var(--color-muted)' }}>
              Kelola sinkronisasi data online (OneDrive, Google Drive, Google Sheets) atau unggah dokumen manual.
            </p>
          </div>
          
          <button
            onClick={() => setIsDataModalOpen(false)}
            style={{
              padding: '6px',
              borderRadius: '50%',
              backgroundColor: '#EDF2F7',
              color: 'var(--color-text-light)',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.2s'
            }}
            title="Tutup dialog"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Tab Selection Area */}
        <div style={{
          padding: '12px 24px 0 24px',
          display: 'flex',
          gap: '8px',
          backgroundColor: '#F8FAFC',
          borderBottom: '1px solid var(--color-border)',
          flexShrink: 0
        }}>
          <button
            onClick={() => setActiveSubTab('onedrive')}
            style={{
              padding: '10px 16px',
              border: 'none',
              borderBottom: activeSubTab === 'onedrive' ? '3px solid var(--color-navy)' : '3px solid transparent',
              backgroundColor: 'transparent',
              color: activeSubTab === 'onedrive' ? 'var(--color-navy)' : 'var(--color-text-light)',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Sumber Data Online
          </button>

          <button
            onClick={() => setActiveSubTab('manual')}
            style={{
              padding: '10px 16px',
              border: 'none',
              borderBottom: activeSubTab === 'manual' ? '3px solid var(--color-navy)' : '3px solid transparent',
              backgroundColor: 'transparent',
              color: activeSubTab === 'manual' ? 'var(--color-navy)' : 'var(--color-text-light)',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Dokumen Manual
          </button>
        </div>

        {/* Main Content Area - Scrollable */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px'
        }}>
          {activeSubTab === 'onedrive' ? (
            <OneDriveManager />
          ) : (
            <DocumentManager />
          )}

          {/* Danger Zone (Reset Data) */}
          <div style={{
            marginTop: '40px',
            padding: '16px 20px',
            border: '1px solid #FED7D7',
            borderRadius: '8px',
            backgroundColor: '#FFF5F5',
          }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#C53030', fontWeight: '700' }}>Danger Zone (Reset Data)</h4>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.78rem', color: '#9B2C2C', lineHeight: '1.4' }}>
              Menghapus semua kategori data online (OneDrive/Google Drive/Google Sheets), dokumen manual, riwayat chat, dan indeks pencarian ChromaDB secara permanen dari server. Tindakan ini tidak dapat dibatalkan.
            </p>
            <button
              onClick={handleResetData}
              disabled={resetting}
              style={{
                backgroundColor: '#E53E3E',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 16px',
                fontSize: '0.78rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                opacity: resetting ? 0.7 : 1
              }}
            >
              {resetting ? 'Mereset...' : '🗑️ Reset Semua Data Aplikasi'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
