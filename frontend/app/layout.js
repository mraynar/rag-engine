// frontend/app/layout.js — Root layout, full-width professional topnav

import Image from 'next/image';
import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine — Asisten Cerdas Terminal Petikemas Surabaya',
  description: 'Sistem tanya-jawab berbasis dokumen untuk PT Terminal Petikemas Surabaya, powered by Gemini AI.',
  icons: { icon: '/images/Logo Pelindo.png' },
};

import AppProviders from './AppProviders';
import CategorySelector from './CategorySelector';
import DataManagementModal from './DataManagementModal';
import AuthNav from './AuthNav';
import AuthModal from './AuthModal';

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <AppProviders>
          <div className="page-shell">

            {/* ── Top navigation bar ── */}
            <header className="topnav" role="banner">
              <div className="topnav-inner">

                {/* Left: Logo + app name */}
                <div className="topnav-brand">
                  <div className="topnav-logo-wrap">
                    <Image
                      src="/images/Logo_TPS.png"
                      alt="Logo PT Terminal Petikemas Surabaya"
                      width={110}
                      height={32}
                      priority
                      style={{ objectFit: 'contain' }}
                    />
                  </div>
                </div>

                {/* Right: Powered-by badge + category selector + auth */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

                  {/* Powered by Gemini */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '5px',
                    fontSize: '0.72rem', fontWeight: '600',
                    color: '#1c6bbf',
                    background: 'var(--color-brand-light)',
                    border: '1px solid rgba(43,127,214,0.2)',
                    padding: '4px 10px',
                    borderRadius: 'var(--r-full)',
                    whiteSpace: 'nowrap',
                  }}>
                    <span style={{
                      width: '6px', height: '6px',
                      background: 'var(--color-brand)',
                      borderRadius: '50%',
                      flexShrink: 0,
                    }} />
                    Powered by Gemini
                  </div>

                  {/* Category dropdown */}
                  <CategorySelector />

                  {/* Vertical divider */}
                  <div className="topnav-divider" />

                  {/* Auth */}
                  <AuthNav />
                </div>

              </div>
            </header>

            {/* ── Page content ── */}
            <main className="main-content" id="main-content">
              {children}
            </main>

          </div>

          {/* Global modals */}
          <DataManagementModal />
          <AuthModal />
        </AppProviders>
      </body>
    </html>
  );
}
