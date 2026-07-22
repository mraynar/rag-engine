// frontend/app/layout.js
// Root layout — wraps every page with the topnav and global design system

import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine',
  description: 'Sistem tanya-jawab berbasis dokumen untuk PT Terminal Petikemas Surabaya',
};

// NavLink with active-state detection is handled client-side in a small component
import NavLinks from './NavLinks';

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <div className="page-shell">
          {/* ---- Top navigation bar ---- */}
          <header className="topnav" role="banner">
            <div className="topnav-inner">
              {/* Brand */}
              <div className="topnav-brand">
                <div className="topnav-logo" aria-hidden="true">
                  {/* Crane / container icon SVG */}
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="14" width="8" height="7" rx="1"/>
                    <rect x="14" y="14" width="8" height="7" rx="1"/>
                    <path d="M6 14V9h12v5"/>
                    <path d="M12 9V3"/>
                    <path d="M9 3h6"/>
                    <path d="M12 3l-5 6"/>
                    <path d="M12 3l5 6"/>
                  </svg>
                </div>
                <span className="topnav-title">
                  RAG Engine
                  <span className="topnav-subtitle">TPS Pelindo</span>
                </span>
              </div>

              {/* Navigation links — client component for active detection */}
              <NavLinks />
            </div>
          </header>

          {/* ---- Page content ---- */}
          <main className="main-content" id="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
