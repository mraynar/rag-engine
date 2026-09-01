'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth, setCookie } from '../AuthContext';
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

function ZapIcon({ size = 15, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function ShieldCheckIcon({ size = 15, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function ChartIcon({ size = 15, className }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
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

    const form = e.currentTarget;
    const formData = new FormData(form);
    
    // Support both DOM values (Safari/browser autofill) and React state
    const cleanEmail = (formData.get('email') || email || '').toString().trim();
    const cleanPassword = (formData.get('password') || password || '').toString();
    const cleanConfirmPassword = (formData.get('confirmPassword') || confirmPassword || '').toString();
    const cleanDisplayName = (formData.get('displayName') || displayName || '').toString().trim();

    if (!cleanEmail || !cleanPassword) {
      setErrorMsg('Email and password are required.');
      return;
    }

    if (mode === 'register') {
      if (cleanPassword.length < 6) {
        setErrorMsg('Password must be at least 6 characters.');
        return;
      }
      if (cleanPassword !== cleanConfirmPassword) {
        setErrorMsg('Confirm password does not match.');
        return;
      }
    }

    setLoading(true);

    try {
      if (mode === 'login') {
        const { data, error } = await login(cleanEmail, cleanPassword);
        if (error) {
          let msg = error.message || 'Failed to sign in. Please verify your email and password.';
          const lowerMsg = (error.message || '').toLowerCase();
          if (lowerMsg.includes('invalid login credentials') || lowerMsg.includes('invalid_grant')) {
            msg = 'Invalid email or password. Please verify your credentials.';
          } else if (lowerMsg.includes('email not confirmed')) {
            msg = 'Email address not confirmed. Please click the confirmation link sent to your email inbox.';
          }
          setErrorMsg(msg);
          setLoading(false);
        } else if (data?.session) {
          setCookie('sb-access-token', data.session.access_token, 7);
          // Hard navigation to trigger clean Next.js server-side cookie evaluation
          window.location.href = redirect;
        } else if (data?.user && !data?.session) {
          setErrorMsg('Account requires email confirmation before signing in. Please check your inbox.');
          setLoading(false);
        } else {
          setErrorMsg('Unable to retrieve session. Please try again.');
          setLoading(false);
        }
      } else {
        // Register
        const name = cleanDisplayName;
        const { data, error } = await register(cleanEmail, cleanPassword, name || cleanEmail.split('@')[0]);
        if (error) {
          setErrorMsg(error.message || 'Registration failed. Please try again.');
          setLoading(false);
        } else if (data?.session) {
          setCookie('sb-access-token', data.session.access_token, 7);
          window.location.href = redirect;
        } else {
          setLoading(false);
          setSuccessMsg('Registration successful! Please check your email inbox to confirm your account before signing in.');
          setTimeout(() => {
            setMode('login');
            setSuccessMsg('');
            setPassword('');
            setConfirmPassword('');
          }, 3000);
        }
      }
    } catch (err) {
      console.error('[Login Error]', err);
      setErrorMsg(err.message || 'An unexpected error occurred. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className={s.card}>
      {/* Left Pane — Logo & Info */}
      <div className={s.leftPane}>
        <div>
          <img src="/images/Logo TPS Monokrom.png" alt="Pelindo Terminal Petikemas TPS Surabaya" className={s.logo} />

          <h1 className={s.leftTitle}>
            Intelligent Assistant &amp; Tabular Data Q&amp;A Portal
          </h1>
          <p className={s.leftOrg}>PT Terminal Petikemas Surabaya</p>
        </div>

        <div className={s.featureList}>
          <div className={s.featureItem}>
            <div className={s.featureIcon}>
              <ZapIcon size={15} />
            </div>
            <span>Real-time Tabular Analytics</span>
          </div>
          <div className={s.featureItem}>
            <div className={s.featureIcon}>
              <ShieldCheckIcon size={15} />
            </div>
            <span>Secure Corporate RAG Engine</span>
          </div>
          <div className={s.featureItem}>
            <div className={s.featureIcon}>
              <ChartIcon size={15} />
            </div>
            <span>Automated Data Insights</span>
          </div>
        </div>
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
              <label htmlFor="displayName" className={s.label}>Full Name</label>
              <div className={s.inputWrapper}>
                <UserIcon size={16} className={s.inputIcon} />
                <input
                  id="displayName"
                  name="displayName"
                  type="text"
                  placeholder="Enter your full name"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  autoComplete="name"
                  required
                  className={s.input}
                />
              </div>
            </div>
          )}

          <div className={s.formGroup}>
            <label htmlFor="email" className={s.label}>Corporate Email</label>
            <div className={s.inputWrapper}>
              <MailIcon size={16} className={s.inputIcon} />
              <input
                id="email"
                name="email"
                type="email"
                placeholder="username@tps.co.id"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoComplete="email"
                required
                className={s.input}
              />
            </div>
          </div>

          <div className={s.formGroup}>
            <label htmlFor="password" className={s.label}>Password</label>
            <div className={s.inputWrapper}>
              <LockIcon size={16} className={s.inputIcon} />
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
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
              <label htmlFor="confirmPassword" className={s.label}>Confirm Password</label>
              <div className={s.inputWrapper}>
                <LockIcon size={16} className={s.inputIcon} />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
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
      <div className={s.bgOrb1} aria-hidden="true" />
      <div className={s.bgOrb2} aria-hidden="true" />
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
