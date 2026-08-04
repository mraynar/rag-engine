// frontend/app/ConversationContext.js
// Manages the active conversation ID with localStorage persistence.
// activeConvId survives tab switches and F5 reloads.
'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const ConversationContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const LS_KEY = 'rag_active_conv_id';

export function ConversationProvider({ children }) {
  // Read initial value from localStorage (null on SSR / first visit)
  const [activeConvId, _setActiveConvId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const initializedRef = useRef(false);

  // Hydrate from localStorage after mount (client-side only)
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    try {
      const stored = localStorage.getItem(LS_KEY);
      if (stored) _setActiveConvId(stored);
    } catch {}
  }, []);

  // Wrap setter to also persist to localStorage
  const setActiveConvId = useCallback((id) => {
    _setActiveConvId(id);
    try {
      if (id) localStorage.setItem(LS_KEY, id);
      else localStorage.removeItem(LS_KEY);
    } catch {}
  }, []);

  // Load conversations list from backend
  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      if (res.ok) setConversations(await res.json());
    } catch {}
    finally { setLoadingConvs(false); }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  return (
    <ConversationContext.Provider
      value={{
        activeConvId,
        setActiveConvId,
        conversations,
        setConversations,
        loadingConvs,
        loadConversations,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversation() {
  const ctx = useContext(ConversationContext);
  if (!ctx) throw new Error('useConversation must be used inside <ConversationProvider>');
  return ctx;
}
