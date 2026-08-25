'use client';

import { useState } from 'react';
import { useAuth } from './AuthContext';
import { useCategory } from './CategoryContext';
import { XIcon } from './icons';

export default function AuthModal() {
  const { isAuthModalOpen, setIsAuthModalOpen } = useCategory();
  const { login, register } = useAuth();
  
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isAuthModalOpen) return null;

  const handleClose = () => {
    setIsAuthModalOpen(false);
    setErrorMsg('');
    setSuccessMsg('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setDisplayName('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!email || !password) {
      setErrorMsg('Email and password are required.');
      return;
    }

    if (mode === 'register') {
      if (password.length < 6) {
        setErrorMsg('Password must be at least 6 characters.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Confirm password does not match.');
        return;
      }
    }

    setLoading(true);

    if (mode === 'login') {
      const { error } = await login(email, password);
      if (error) {
        setErrorMsg(error.message || 'Failed to sign in. Please check your email and password.');
        setLoading(false);
      } else {
        setLoading(false);
        handleClose();
      }
    } else {
      // Register
      const name = displayName.strip ? displayName.strip() : displayName;
      const { error } = await register(email, password, name || email.split('@')[0]);
      if (error) {
        setErrorMsg(error.message || 'Registration failed. Please try again.');
        setLoading(false);
      } else {
        setLoading(false);
        setSuccessMsg('Registration successful! Please check your email for confirmation if required.');
        setTimeout(() => {
          setMode('login');
          setSuccessMsg('');
          setPassword('');
          setConfirmPassword('');
        }, 3000);
      }
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(11, 47, 92, 0.4)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 99999,
      fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{
        backgroundColor: '#fff',
        width: '90%',
        maxWidth: '420px',
        borderRadius: '12px',
        boxShadow: 'var(--shadow-lg)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative'
      }}>
        
        {/* Header */}
        <div style={{
          padding: '24px 24px 16px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--color-navy)', fontWeight: '700' }}>
            {mode === 'login' ? 'Sign In to Account' : 'Register New Account'}
          </h3>
          
          <button
            onClick={handleClose}
            style={{
              padding: '6px',
              borderRadius: '50%',
              backgroundColor: '#EDF2F7',
              color: 'var(--color-text-light)',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.2s'
            }}
            title="Close dialog"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {errorMsg && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: '#FFF5F5',
              border: '1px solid #FED7D7',
              borderRadius: '6px',
              color: '#C53030',
              fontSize: '0.8rem',
              lineHeight: '1.4'
            }}>
              {errorMsg}
            </div>
          )}

          {successMsg && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: '#F0FFF4',
              border: '1px solid #C6F6D5',
              borderRadius: '6px',
              color: '#22543D',
              fontSize: '0.8rem',
              lineHeight: '1.4'
            }}>
              {successMsg}
            </div>
          )}

          {mode === 'register' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="displayName" style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--color-text-light)' }}>
                Display Name (Optional)
              </label>
              <input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Example: John Doe"
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.85rem',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
              />
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor="authEmail" style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--color-text-light)' }}>
              Email Address
            </label>
            <input
              id="authEmail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              required
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                border: '1px solid var(--color-border)',
                fontSize: '0.85rem',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor="authPassword" style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--color-text-light)' }}>
              Password
            </label>
            <input
              id="authPassword"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                border: '1px solid var(--color-border)',
                fontSize: '0.85rem',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
          </div>

          {mode === 'register' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="confirmPassword" style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--color-text-light)' }}>
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.85rem',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '8px',
              padding: '12px',
              backgroundColor: 'var(--color-navy)',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'opacity 0.2s',
              opacity: loading ? 0.75 : 1,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center'
            }}
          >
            {loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Sign Up')}
          </button>

          {/* Footer toggle link */}
          <div style={{
            marginTop: '8px',
            textAlign: 'center',
            fontSize: '0.78rem',
            color: 'var(--color-muted)'
          }}>
            {mode === 'login' ? (
              <>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => { setMode('register'); setErrorMsg(''); }}
                  style={{ color: 'var(--color-navy)', fontWeight: '600', textDecoration: 'underline', border: 'none', background: 'none', cursor: 'pointer' }}
                >
                  Sign Up here
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => { setMode('login'); setErrorMsg(''); }}
                  style={{ color: 'var(--color-navy)', fontWeight: '600', textDecoration: 'underline', border: 'none', background: 'none', cursor: 'pointer' }}
                >
                  Sign In here
                </button>
              </>
            )}
          </div>
        </form>

      </div>
    </div>
  );
}
