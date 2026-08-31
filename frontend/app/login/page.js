'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '../AuthContext';
import s from './login.module.css';

// SVG Icons
function MailIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

function LockIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function UserIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function EyeIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

function AlertIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function CheckCircleIcon({ size = 16, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/';

  const { login, register } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

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
        setErrorMsg(error.message || 'Failed to sign in. Please verify your email and password.');
        setLoading(false);
      } else {
        router.replace(redirect);
      }
    } else {
      // Register
      const name = displayName.trim();
      const { error } = await register(email, password, name || email.split('@')[0]);
      if (error) {
        setErrorMsg(error.message || 'Registration failed. Please try again.');
        setLoading(false);
      } else {
        setLoading(false);
        setSuccessMsg('Registration successful! Please check your email for confirmation or sign in directly.');
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
    <div className={s.card}>
      {/* Left Pane — Logo & Info */}
      <div className={s.leftPane}>
        <img src="/images/Logo TPS Monokrom.png" alt="Pelindo Terminal Petikemas TPS Surabaya" className={s.logo} style={{ height: '70px', marginBottom: '24px' }} />
        <p className={s.leftDesc}>
          Intelligent Assistant & Tabular Data Q&A Portal for PT Terminal Petikemas Surabaya
        </p>
      </div>

      {/* Right Pane — Login Form */}
      <div className={s.rightPane}>
        <div className={s.header}>
          <p className={s.subtitle}>Please sign in with your corporate credentials to start using the RAG Engine.</p>
        </div>

        <div className={s.tabGroup}>
          <button
            type="button"
            onClick={() => { setMode('login'); setErrorMsg(''); setSuccessMsg(''); }}
            className={`${s.tab} ${mode === 'login' ? s.tabActive : ''}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setErrorMsg(''); setSuccessMsg(''); }}
            className={`${s.tab} ${mode === 'register' ? s.tabActive : ''}`}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className={s.form}>
          {errorMsg && (
            <div className={`${s.alert} ${s.alertError}`}>
              <AlertIcon size={16} className={s.alertIcon} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className={`${s.alert} ${s.alertSuccess}`}>
              <CheckCircleIcon size={16} className={s.alertIcon} />
              <span>{successMsg}</span>
            </div>
          )}

          {mode === 'register' && (
            <div className={s.formGroup}>
              <label className={s.label}>Full Name</label>
              <div className={s.inputWrapper}>
                <UserIcon size={16} className={s.inputIcon} />
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  required
                  className={s.input}
                />
              </div>
            </div>
          )}

          <div className={s.formGroup}>
            <label className={s.label}>Corporate Email</label>
            <div className={s.inputWrapper}>
              <MailIcon size={16} className={s.inputIcon} />
              <input
                type="email"
                placeholder="username@tps.co.id"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className={s.input}
              />
            </div>
          </div>

          <div className={s.formGroup}>
            <label className={s.label}>Password</label>
            <div className={s.inputWrapper}>
              <LockIcon size={16} className={s.inputIcon} />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className={s.input}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className={s.eyeButton}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div className={s.formGroup}>
              <label className={s.label}>Confirm Password</label>
              <div className={s.inputWrapper}>
                <LockIcon size={16} className={s.inputIcon} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  required
                  className={s.input}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={s.eyeButton}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
                </button>
              </div>
            </div>
          )}

          <button type="submit" disabled={loading} className={s.submitBtn}>
            {loading ? (
              <>
                <div className={s.spinner} />
                <span>Processing...</span>
              </>
            ) : mode === 'login' ? (
              <span>Sign In to RAG Engine</span>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className={s.container}>
      <Suspense fallback={
        <div className={s.card} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
          <div className={s.spinner} style={{ width: '32px', height: '32px' }} />
        </div>
      }>
        <LoginFormContent />
      </Suspense>
    </div>
  );
}
