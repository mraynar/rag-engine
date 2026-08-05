// frontend/app/CategoryContext.js
'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const CategoryContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const LS_KEY = 'rag_selected_category';

export function CategoryProvider({ children }) {
  const [selectedCategory, _setSelectedCategory] = useState("Semua Data");
  const initializedRef = useRef(false);

  // Read initial value from localStorage on client-side mount
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    try {
      const stored = localStorage.getItem(LS_KEY);
      console.log('CategoryContext mount. Stored key:', stored);
      if (stored) _setSelectedCategory(stored);
    } catch (e) {
      console.error('CategoryContext mount error:', e);
    }
  }, []);

  // Wrapped setter to also update localStorage
  const setSelectedCategory = useCallback((category) => {
    console.log('CategoryContext setSelectedCategory called with:', category);
    _setSelectedCategory(category);
    try {
      if (category) {
        localStorage.setItem(LS_KEY, category);
        console.log('CategoryContext saved to LS:', category);
      } else {
        localStorage.removeItem(LS_KEY);
      }
    } catch (e) {
      console.error('CategoryContext setItem error:', e);
    }
  }, []);

  const [categories, setCategories] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
  
  const [documents, setDocuments] = useState([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);

  const [isDataModalOpen, setIsDataModalOpen] = useState(false);

  const refreshCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sources`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
      }
    } catch (err) {
      console.error('Failed to load categories', err);
    } finally {
      setLoadingCategories(false);
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Failed to load manual documents', err);
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    refreshCategories();
    refreshDocuments();
  }, [refreshCategories, refreshDocuments]);

  return (
    <CategoryContext.Provider
      value={{
        selectedCategory,
        setSelectedCategory,
        categories,
        loadingCategories,
        refreshCategories,
        documents,
        loadingDocuments,
        refreshDocuments,
        isDataModalOpen,
        setIsDataModalOpen,
      }}
    >
      {children}
    </CategoryContext.Provider>
  );
}

export function useCategory() {
  const ctx = useContext(CategoryContext);
  if (!ctx) throw new Error('useCategory must be used inside <CategoryProvider>');
  return ctx;
}
