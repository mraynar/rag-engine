'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { supabase } from './supabase';

const AuthContext = createContext(null);
const SAVED_ACCOUNTS_KEY = 'rag_saved_accounts';

export function setCookie(name, value, days) {
  let expires = "";
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    expires = "; expires=" + date.toUTCString();
  }
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const secureFlag = isSecure ? "; Secure" : "";
  document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax" + secureFlag;
}

export function deleteCookie(name) {
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const secureFlag = isSecure ? "; Secure" : "";
  document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT; SameSite=Lax' + secureFlag;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savedAccounts, setSavedAccounts] = useState([]);

  // Load saved accounts from localStorage
  const loadSavedAccounts = useCallback(() => {
    try {
      const stored = localStorage.getItem(SAVED_ACCOUNTS_KEY);
      if (stored) {
        setSavedAccounts(JSON.parse(stored));
      } else {
        setSavedAccounts([]);
      }
    } catch {
      setSavedAccounts([]);
    }
  }, []);

  // Save/Update account entry in localStorage
  const persistSavedAccount = useCallback((s) => {
    if (!s?.user) return;
    try {
      const stored = localStorage.getItem(SAVED_ACCOUNTS_KEY);
      let list = stored ? JSON.parse(stored) : [];
      const index = list.findIndex(a => a.id === s.user.id);
      const entry = {
        id: s.user.id,
        email: s.user.email,
        display_name: s.user.user_metadata?.display_name || s.user.email.split('@')[0],
        access_token: s.access_token,
        refresh_token: s.refresh_token,
        user: s.user,
        updated_at: new Date().toISOString()
      };
      if (index >= 0) {
        list[index] = entry;
      } else {
        list.push(entry);
      }
      localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(list));
      setSavedAccounts(list);
    } catch (err) {
      console.error('[AuthContext] Error persisting saved account:', err);
    }
  }, []);

  useEffect(() => {
    loadSavedAccounts();

    // 1. Check initial active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session) {
        setCookie('sb-access-token', session.access_token, 7);
        persistSavedAccount(session);
      } else {
        deleteCookie('sb-access-token');
      }
      setLoading(false);
    });

    // 2. Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, currentSession) => {
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
        setLoading(false);

        if (currentSession) {
          setCookie('sb-access-token', currentSession.access_token, 7);
          persistSavedAccount(currentSession);
        } else {
          deleteCookie('sb-access-token');
        }

        if (event === 'SIGNED_OUT') {
          localStorage.removeItem('rag_active_conv_id');
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [loadSavedAccounts, persistSavedAccount]);

  // Login handler
  const login = async (email, password) => {
    try {
      const cleanEmail = (email || '').trim();
      const { data, error } = await supabase.auth.signInWithPassword({
        email: cleanEmail,
        password,
      });
      if (data?.session) {
        setSession(data.session);
        setUser(data.session.user ?? null);
        setCookie('sb-access-token', data.session.access_token, 7);
        persistSavedAccount(data.session);
      }
      return { data, error };
    } catch (err) {
      return { data: null, error: err };
    }
  };

  // Register handler
  const register = async (email, password, displayName) => {
    try {
      const cleanEmail = (email || '').trim();
      const { data, error } = await supabase.auth.signUp({
        email: cleanEmail,
        password,
        options: {
          data: {
            display_name: displayName,
          },
        },
      });
      if (data?.session) {
        setSession(data.session);
        setUser(data.session.user ?? null);
        setCookie('sb-access-token', data.session.access_token, 7);
        persistSavedAccount(data.session);
      }
      return { data, error };
    } catch (err) {
      return { data: null, error: err };
    }
  };

  // Switch to a specific saved account
  const switchAccount = async (account) => {
    try {
      if (!account?.access_token || !account?.refresh_token) {
        throw new Error('No refresh token available');
      }
      const { data, error } = await supabase.auth.setSession({
        access_token: account.access_token,
        refresh_token: account.refresh_token,
      });
      if (error) throw error;
      if (data?.session) {
        setSession(data.session);
        setUser(data.session.user ?? null);
        setCookie('sb-access-token', data.session.access_token, 7);
        persistSavedAccount(data.session);
        // Reload page so all contexts and conversations re-initialize cleanly
        window.location.reload();
      }
      return { data, error: null };
    } catch (err) {
      console.error('[AuthContext] switchAccount error:', err);
      return { data: null, error: err };
    }
  };

  // Remove saved account entry
  const removeSavedAccount = (userId) => {
    try {
      const stored = localStorage.getItem(SAVED_ACCOUNTS_KEY);
      let list = stored ? JSON.parse(stored) : [];
      list = list.filter(a => a.id !== userId);
      localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(list));
      setSavedAccounts(list);
    } catch (err) {
      console.error('[AuthContext] error removing saved account:', err);
    }
  };

  const logout = async () => {
    try {
      deleteCookie('sb-access-token');
      setUser(null);
      setSession(null);
      supabase.auth.signOut().catch(() => {});
      window.location.href = '/login';
    } catch (err) {
      console.error('[AuthContext] Sign out error:', err);
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        savedAccounts,
        login,
        register,
        logout,
        switchAccount,
        removeSavedAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside an <AuthProvider>');
  return ctx;
}
