'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from './supabase';

const AuthContext = createContext(null);

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

  useEffect(() => {
    // 1. Check initial active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session) {
        setCookie('sb-access-token', session.access_token, 7);
      } else {
        deleteCookie('sb-access-token');
      }
      setLoading(false);
    });

    // 2. Listen for auth changes (login, logout, tab sync, token refreshed)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, currentSession) => {
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
        setLoading(false);

        if (currentSession) {
          setCookie('sb-access-token', currentSession.access_token, 7);
        } else {
          deleteCookie('sb-access-token');
        }

        if (event === 'SIGNED_OUT') {
          // Clear any client side local state keys that shouldn't leak
          localStorage.removeItem('rag_active_conv_id');
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

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
      }
      return { data, error };
    } catch (err) {
      return { data: null, error: err };
    }
  };

  const logout = async () => {
    try {
      deleteCookie('sb-access-token');
      setUser(null);
      setSession(null);
      // Fire-and-forget signout in background without blocking navigation
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
        login,
        register,
        logout,
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
