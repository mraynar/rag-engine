// frontend/app/AppProviders.js
// 'use client' wrapper — needed because layout.js must stay a Server Component
// (it exports `metadata`). All client-side context providers live here.
'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useUpload, UploadProvider } from './UploadContext';
import styles from './upload.module.css';

// ---- Inline SVG icons (no emoji, consistent with the rest of the app) ----

function UploadIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
}

function CheckIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function AlertIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function XIcon({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function SpinnerIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      aria-hidden="true" className={styles.spin}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

// ---- Upload status pill shown in the topnav ----

function UploadStatusArea() {
  const { uploads, dismissUpload } = useUpload();
  const router = useRouter();

  if (!uploads.length) return null;

  return (
    <div className={styles.pillStack} aria-live="polite">
      {uploads.map((u) => (
        <div
          key={u.id}
          className={`${styles.pill} ${
            u.status === 'uploading' ? styles.pillUploading :
            u.status === 'success'  ? styles.pillSuccess   :
                                      styles.pillError
          }`}
          role={u.status !== 'uploading' ? 'alert' : undefined}
          title={u.message || `Mengupload: ${u.filename}`}
        >
          {/* Icon */}
          <span className={styles.pillIcon}>
            {u.status === 'uploading' && <SpinnerIcon size={13} />}
            {u.status === 'success'   && <CheckIcon   size={13} />}
            {u.status === 'error'     && <AlertIcon   size={13} />}
          </span>

          {/* Label */}
          <span className={styles.pillLabel}>
            {u.status === 'uploading'
              ? `Mengupload: ${u.filename}`
              : u.message}
          </span>

          {/* Navigate to /documents on click */}
          {u.status !== 'uploading' && (
            <button
              className={styles.pillNav}
              onClick={() => router.push('/documents')}
              aria-label="Buka halaman dokumen"
            >
              Lihat
            </button>
          )}

          {/* Dismiss */}
          {u.status !== 'uploading' && (
            <button
              className={styles.pillDismiss}
              onClick={() => dismissUpload(u.id)}
              aria-label="Tutup notifikasi"
            >
              <XIcon size={11} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

// ---- Root providers wrapper ----

export default function AppProviders({ children }) {
  return (
    <UploadProvider>
      <UploadStatusArea />
      {children}
    </UploadProvider>
  );
}
