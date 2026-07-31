'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const CategoryContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function CategoryProvider({ children }) {
  const [selectedCategory, setSelectedCategory] = useState("Semua Data");
  const [categories, setCategories] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(true);

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

  useEffect(() => {
    refreshCategories();
  }, [refreshCategories]);

  return (
    <CategoryContext.Provider
      value={{
        selectedCategory,
        setSelectedCategory,
        categories,
        loadingCategories,
        refreshCategories,
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
