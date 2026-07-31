// frontend/app/layout.js
// Root layout — wraps every page with the topnav and global design system.

import Image from 'next/image';
import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine',
  description: 'Sistem tanya-jawab berbasis dokumen untuk PT Terminal Petikemas Surabaya',
  icons: {
    icon: '/images/Logo Pelindo.png',
  },
};

import AppProviders from './AppProviders';
import CategorySelector from './CategorySelector';

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <AppProviders>
          <div className="page-shell">
            {/* ---- Top navigation bar (Unified Light theme matching reference) ---- */}
            <header className="topnav" role="banner" style={{ position: 'relative' }}>
              <div className="topnav-inner" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>

                {/* Left: Colored Pelindo Brand Logo */}
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <Image
                    src="/images/Logo_TPS.png"
                    alt="Logo PT Terminal Petikemas Surabaya"
                    width={120}
                    height={36}
                    priority
                    style={{ objectFit: 'contain' }}
                  />
                </div>



                {/* Right: Powered by Gemini badge + Dropdown Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  
                  {/* Powered by Gemini Badge */}
                  <div style={{
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    color: '#2B6CB0',
                    backgroundColor: '#EBF8FF',
                    padding: '4px 10px',
                    borderRadius: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <span style={{ display: 'inline-block', width: '6px', height: '6px', backgroundColor: '#3182CE', borderRadius: '50%' }} />
                    Powered by Gemini
                  </div>

                  {/* Dropdown Category Selector */}
                  <CategorySelector />
                </div>

              </div>
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
