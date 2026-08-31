// frontend/app/layout.js — Simplified Root Layout

import './globals.css';

export const metadata = {
  title: 'TPS RAG Engine — Intelligent Assistant',
  description: 'Document-based Q&A and analysis portal for PT Terminal Petikemas Surabaya, powered by Gemini AI.',
  icons: { icon: '/images/Logo Pelindo.png' },
};

import AppProviders from './AppProviders';
import DataManagementModal from './DataManagementModal';
import AuthModal from './AuthModal';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
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
