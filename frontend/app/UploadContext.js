// frontend/app/UploadContext.js
// Global upload state — persists across page navigation.
// The actual fetch() happens here so unmounting /documents doesn't abort it.
'use client';

import { createContext, useCallback, useContext, useRef, useState } from 'react';

const UploadContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let _nextId = 0;

export function UploadProvider({ children }) {
  // uploads: { id, filename, status: 'uploading'|'success'|'error', message }[]
  const [uploads, setUploads] = useState([]);

  // Callback registered by the Documents page to refresh its list on completion
  const onCompleteRef = useRef(null);

  const registerRefreshCallback = useCallback((fn) => {
    onCompleteRef.current = fn;
  }, []);

  const unregisterRefreshCallback = useCallback(() => {
    onCompleteRef.current = null;
  }, []);

  const dismissUpload = useCallback((id) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  }, []);

  /**
   * Start an upload — the fetch() is fired here in the provider, not in the
   * page component, so navigating away does not abort it.
   *
   * @param {File} file
   * @param {string} label  optional user-supplied label
   * @returns {{ id: number }}  the upload record id so callers can track it
   */
  const startUpload = useCallback((file, label) => {
    const id = ++_nextId;
    const filename = file.name;

    setUploads((prev) => [
      ...prev,
      { id, filename, status: 'uploading', message: '' },
    ]);

    const formData = new FormData();
    formData.append('file', file);
    if (label && label.trim()) formData.append('label', label.trim());

    fetch(`${API_BASE}/documents`, { method: 'POST', body: formData })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
        const chunkCount = data.document?.chunk_count ?? '?';
        setUploads((prev) =>
          prev.map((u) =>
            u.id === id
              ? {
                  ...u,
                  status: 'success',
                  message: `"${filename}" diupload (${chunkCount} chunk)`,
                }
              : u
          )
        );
        // If Documents page is still mounted, refresh its list
        onCompleteRef.current?.();
      })
      .catch((err) => {
        setUploads((prev) =>
          prev.map((u) =>
            u.id === id
              ? { ...u, status: 'error', message: err.message || 'Upload gagal' }
              : u
          )
        );
      });

    return { id };
  }, []);

  return (
    <UploadContext.Provider
      value={{ uploads, startUpload, dismissUpload, registerRefreshCallback, unregisterRefreshCallback }}
    >
      {children}
    </UploadContext.Provider>
  );
}

export function useUpload() {
  const ctx = useContext(UploadContext);
  if (!ctx) throw new Error('useUpload must be used inside <UploadProvider>');
  return ctx;
}
