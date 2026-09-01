// frontend/app/ConversationContext.js
// Centralized state manager for all chat conversations and messages.
// Handles Supabase authenticated database sessions and local guest storage transparently.
'use client';

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';

const ConversationContext = createContext(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL;
const GUEST_CONVS_KEY = 'rag_guest_conversations';

export function ConversationProvider({ children }) {
  const { user, session, loading: authLoading } = useAuth();
  
  const [activeConvId, _setActiveConvId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const messagesCacheRef = useRef({});

  // Synchronous cache reader for instant UI render
  const getCachedConversation = useCallback((id) => {
    return messagesCacheRef.current[id] || null;
  }, []);
  const initializedRef = useRef(false);

  // Dynamic localStorage key for active conversation ID to prevent data leakage between users
  const getActiveConvIdKey = useCallback(() => {
    return user ? `rag_active_conv_id_${user.id}` : 'rag_active_conv_id_guest';
  }, [user]);

  // Hydrate active conversation ID from localStorage
  useEffect(() => {
    if (authLoading) return;
    try {
      const key = getActiveConvIdKey();
      const stored = localStorage.getItem(key);
      if (stored) {
        _setActiveConvId(stored);
      } else {
        _setActiveConvId(null);
      }
    } catch {}
  }, [user, authLoading, getActiveConvIdKey]);

  // Wrap setter to persist to user-specific or guest localStorage key
  const setActiveConvId = useCallback((id) => {
    _setActiveConvId(id);
    try {
      const key = getActiveConvIdKey();
      if (id) {
        localStorage.setItem(key, id);
      } else {
        localStorage.removeItem(key);
      }
    } catch {}
  }, [getActiveConvIdKey]);

  // Authenticated headers helper
  const getAuthHeaders = useCallback(() => {
    const headers = { 'Content-Type': 'application/json' };
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
    return headers;
  }, [session]);

  // Load conversations list
  const loadConversations = useCallback(async () => {
    if (authLoading) return;
    setLoadingConvs(true);

    if (user) {
      // Authenticated User: Load from database
      try {
        const res = await fetch(`${API_BASE}/conversations`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          setConversations(data);
        }
      } catch (err) {
        console.error('[loadConversations] Error fetching user conversations:', err);
      } finally {
        setLoadingConvs(false);
      }
    } else {
      // Guest User: Load from localStorage
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        let guestConvs = stored ? JSON.parse(stored) : [];
        
        // Sort: pinned first, then updated_at desc
        guestConvs.sort((a, b) => {
          if (a.pinned && !b.pinned) return -1;
          if (!a.pinned && b.pinned) return 1;
          return new Date(b.updated_at) - new Date(a.updated_at);
        });

        // Compute message count for summaries
        const summaries = guestConvs.map(c => ({
          id: c.id,
          title: c.title,
          title_source: c.title_source || 'auto',
          pinned: c.pinned,
          created_at: c.created_at,
          updated_at: c.updated_at,
          message_count: c.messages ? c.messages.length : 0
        }));

        setConversations(summaries);
      } catch (err) {
        console.error('[loadConversations] Error loading guest conversations:', err);
      } finally {
        setLoadingConvs(false);
      }
    }
  }, [user, authLoading, getAuthHeaders]);

  // Reload when authentication state updates
  useEffect(() => {
    loadConversations();
  }, [user, authLoading, loadConversations]);

  // Create conversation
  const createConversation = async () => {
    if (user) {
      // Database backed
      try {
        const res = await fetch(`${API_BASE}/conversations`, {
          method: 'POST',
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          // Optimistically update conversation list
          setConversations(prev => [data, ...prev.filter(c => c.id !== data.id)]);
          return data;
        }
      } catch (err) {
        console.error('[createConversation] error:', err);
      }
      return null;
    } else {
      // Local guest storage
      const newConv = {
        id: `conv_guest_${Math.random().toString(36).substring(2, 10)}`,
        title: 'New conversation',
        title_source: 'auto',
        pinned: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: []
      };

      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        const guestConvs = stored ? JSON.parse(stored) : [];
        guestConvs.unshift(newConv);
        localStorage.setItem(GUEST_CONVS_KEY, JSON.stringify(guestConvs));
        setConversations(prev => [newConv, ...prev.filter(c => c.id !== newConv.id)]);
        return newConv;
      } catch (err) {
        console.error('[createConversation] guest error:', err);
      }
      return null;
    }
  };

  // Get conversation details including messages
  const getConversation = async (id) => {
    if (user) {
      try {
        const res = await fetch(`${API_BASE}/conversations/${id}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          if (data?.id) {
            messagesCacheRef.current[data.id] = data;
          }
          return data;
        }
      } catch (err) {
        console.error('[getConversation] error:', err);
      }
      return messagesCacheRef.current[id] || null;
    } else {
      // Guest
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        const guestConvs = stored ? JSON.parse(stored) : [];
        const found = guestConvs.find(c => c.id === id);
        if (found) messagesCacheRef.current[id] = found;
        return found || null;
      } catch (err) {
        console.error('[getConversation] guest error:', err);
      }
      return messagesCacheRef.current[id] || null;
    }
  };

  // Rename conversation
  const renameConversation = async (id, title) => {
    const cleanTitle = title.trim() || 'New conversation';
    
    // Optimistic UI update
    setConversations(prev => prev.map(c => c.id === id ? { ...c, title: cleanTitle, title_source: 'manual' } : c));

    if (user) {
      try {
        const res = await fetch(`${API_BASE}/conversations/${id}`, {
          method: 'PATCH',
          headers: getAuthHeaders(),
          body: JSON.stringify({ title: cleanTitle })
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.error('[renameConversation] error:', err);
        await loadConversations();
      }
      return null;
    } else {
      // Guest
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        const guestConvs = stored ? JSON.parse(stored) : [];
        const index = guestConvs.findIndex(c => c.id === id);
        if (index !== -1) {
          guestConvs[index].title = cleanTitle;
          guestConvs[index].title_source = 'manual';
          guestConvs[index].updated_at = new Date().toISOString();
          localStorage.setItem(GUEST_CONVS_KEY, JSON.stringify(guestConvs));
          return guestConvs[index];
        }
      } catch (err) {
        console.error('[renameConversation] guest error:', err);
      }
      return null;
    }
  };

  // Pin/Unpin conversation
  const togglePin = async (id, pinned) => {
    // Optimistic UI update & sort
    setConversations(prev => {
      const next = prev.map(c => c.id === id ? { ...c, pinned } : c);
      next.sort((a, b) => {
        if (a.pinned && !b.pinned) return -1;
        if (!a.pinned && b.pinned) return 1;
        return new Date(b.updated_at) - new Date(a.updated_at);
      });
      return next;
    });

    if (user) {
      try {
        const res = await fetch(`${API_BASE}/conversations/${id}`, {
          method: 'PATCH',
          headers: getAuthHeaders(),
          body: JSON.stringify({ pinned })
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.error('[togglePin] error:', err);
        await loadConversations();
      }
      return null;
    } else {
      // Guest
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        const guestConvs = stored ? JSON.parse(stored) : [];
        const index = guestConvs.findIndex(c => c.id === id);
        if (index !== -1) {
          guestConvs[index].pinned = pinned;
          guestConvs[index].updated_at = new Date().toISOString();
          localStorage.setItem(GUEST_CONVS_KEY, JSON.stringify(guestConvs));
          return guestConvs[index];
        }
      } catch (err) {
        console.error('[togglePin] guest error:', err);
      }
      return null;
    }
  };

  // Delete conversation
  const deleteConversation = async (id) => {
    // 1. Optimistic UI update: remove immediately from state
    setConversations(prev => {
      const remaining = prev.filter(c => c.id !== id);
      if (activeConvId === id) {
        const nextActive = remaining.length > 0 ? remaining[0].id : null;
        _setActiveConvId(nextActive);
        try {
          const key = getActiveConvIdKey();
          if (nextActive) localStorage.setItem(key, nextActive);
          else localStorage.removeItem(key);
        } catch {}
      }
      return remaining;
    });

    if (user) {
      try {
        const res = await fetch(`${API_BASE}/conversations/${id}`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        });
        if (res.ok) {
          return true;
        }
      } catch (err) {
        console.error('[deleteConversation] error:', err);
        // Rollback from server if failed
        await loadConversations();
      }
      return false;
    } else {
      // Guest
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        let guestConvs = stored ? JSON.parse(stored) : [];
        guestConvs = guestConvs.filter(c => c.id !== id);
        localStorage.setItem(GUEST_CONVS_KEY, JSON.stringify(guestConvs));
        return true;
      } catch (err) {
        console.error('[deleteConversation] guest error:', err);
      }
      return false;
    }
  };

  // Post chat message to backend `/chat` endpoint
  const postChatMessage = async (convId, messageText, category) => {
    // 1. Post to backend
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        message: messageText,
        conversation_id: convId,
        category: category === 'All Data' ? null : category,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${res.status})`);
    }

    const data = await res.json();

    // 2. If guest, append the user and assistant messages manually to localStorage
    if (!user) {
      try {
        const stored = localStorage.getItem(GUEST_CONVS_KEY);
        const guestConvs = stored ? JSON.parse(stored) : [];
        const index = guestConvs.findIndex(c => c.id === convId);
        if (index !== -1) {
          const conv = guestConvs[index];
          const nowStr = new Date().toISOString();
          
          const isFirstMessage = (conv.messages.length === 0);

          conv.messages.push({
            role: 'user',
            content: messageText,
            timestamp: nowStr
          });

          conv.messages.push({
            role: 'assistant',
            content: data.answer,
            sources: data.sources || [],
            timestamp: nowStr
          });

          conv.updated_at = nowStr;

          // Client-side simple auto-title generation for guest
          if (isFirstMessage && conv.title_source === 'auto') {
            const cleanMessage = messageText.trim();
            conv.title = cleanMessage.length > 40 
              ? cleanMessage.substring(0, 37) + '...'
              : cleanMessage;
          }

          localStorage.setItem(GUEST_CONVS_KEY, JSON.stringify(guestConvs));
          await loadConversations();
        }
      } catch (err) {
        console.error('[postChatMessage] Error saving guest messages:', err);
      }
    }

    return data;
  };

  return (
    <ConversationContext.Provider
      value={{
        activeConvId,
        setActiveConvId,
        conversations,
        setConversations,
        loadingConvs,
        loadConversations,
        createConversation,
        getConversation,
        getCachedConversation,
        renameConversation,
        togglePin,
        deleteConversation,
        postChatMessage
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
