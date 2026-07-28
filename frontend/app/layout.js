// frontend/app/layout.js
// Root layout — wraps every page with the topnav and global design system.
// Must stay a Server Component (exports `metadata`), so all client-side
// providers live in AppProviders.js which is imported here.

import Image from 'next/image';
import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine',
  description: 'Sistem tanya-jawab berbasis dokumen untuk PT Terminal Petikemas Surabaya',
  icons: {
    icon: '/images/Logo Pelindo.png',
  },
};

import NavLinks from './NavLinks';
import AppProviders from './AppProviders';

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <AppProviders>
          <div className="page-shell">
            {/* ---- Top navigation bar ---- */}
            <header className="topnav" role="banner" style={{ position: 'relative' }}>
              <div className="topnav-inner">

                {/* Brand — logo image + app label */}
                <div className="topnav-brand">
                  <div className="topnav-logo-wrap">
                    <Image
                      src="/images/Logo TPS Monokrom.png"
                      alt="Logo PT Terminal Petikemas Surabaya"
                      width={110}
                      height={44}
                      priority
                      style={{ objectFit: 'contain', display: 'block' }}
                    />
                  </div>

                  {/* Divider */}
                  <span className="topnav-divider" aria-hidden="true" />

                  <div className="topnav-app-label">
                    <span className="topnav-app-name">RAG Engine</span>
                    <span className="topnav-app-sub">Sistem Manajemen Model &amp; Dokumen</span>
                  </div>
                </div>

                {/* Navigation links */}
                <NavLinks />
              </div>
              {/* Upload status pill — rendered by AppProviders, positioned absolutely */}
            </header>

            {/* ---- Page content ---- */}
            <main className="main-content" id="main-content">
              {children}
            </main>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
