// frontend/app/layout.js — Simplified Root Layout

import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine — Asisten Cerdas Terminal Petikemas Surabaya',
  description: 'Sistem tanya-jawab berbasis dokumen untuk PT Terminal Petikemas Surabaya, powered by Gemini AI.',
  icons: { icon: '/images/Logo Pelindo.png' },
};

import AppProviders from './AppProviders';
import DataManagementModal from './DataManagementModal';
import AuthModal from './AuthModal';

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>
        <AppProviders>
          <div className="page-shell">
            {children}
          </div>
          <DataManagementModal />
          <AuthModal />
        </AppProviders>
      </body>
    </html>
  );
}
