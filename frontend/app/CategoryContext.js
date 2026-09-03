// frontend/app/CategoryContext.js
'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';

const CategoryContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL;
const LS_KEY = 'rag_selected_category';

export function CategoryProvider({ children }) {
  const { session, loading: authLoading } = useAuth();
  const [selectedCategory, _setSelectedCategory] = useState("All Data");
  const initializedRef = useRef(false);

  // Read initial value from localStorage on client-side mount
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    try {
      const stored = localStorage.getItem(LS_KEY);
      if (stored) _setSelectedCategory(stored);
    } catch (e) {
      console.error('CategoryContext mount error:', e);
    }
  }, []);

  // Wrapped setter to also update localStorage
  const setSelectedCategory = useCallback((category) => {
    _setSelectedCategory(category);
    try {
      if (category) {
        localStorage.setItem(LS_KEY, category);
      } else {
        localStorage.removeItem(LS_KEY);
      }
    } catch (e) {
      console.error('CategoryContext setItem error:', e);
    }
  }, []);

  const [categories, setCategories] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(true);

  const [isDataModalOpen, setIsDataModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const getHeaders = useCallback(() => {
    const h = {};
    if (session?.access_token) {
      h['Authorization'] = `Bearer ${session.access_token}`;
    }
    return h;
  }, [session]);

  const refreshCategories = useCallback(async () => {
    if (authLoading) return;
    try {
      const res = await fetch(`${API_BASE}/sources`, {
        headers: getHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
      }
    } catch (err) {
      console.error('Failed to load categories', err);
    } finally {
      setLoadingCategories(false);
    }
  }, [authLoading, getHeaders]);

  useEffect(() => {
    refreshCategories();
  }, [session, refreshCategories]);

  return (
    <CategoryContext.Provider
      value={{
        selectedCategory,
        setSelectedCategory,
        categories,
        loadingCategories,
        refreshCategories,
        isDataModalOpen,
        setIsDataModalOpen,
        isAuthModalOpen,
        setIsAuthModalOpen,
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
