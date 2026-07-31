// frontend/app/CategoryContext.js
'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const CategoryContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function CategoryProvider({ children }) {
  const [selectedCategory, setSelectedCategory] = useState("Semua Data");
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
