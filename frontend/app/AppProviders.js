'use client';

import { CategoryProvider } from './CategoryContext';
import { ConversationProvider } from './ConversationContext';
import { AuthProvider } from './AuthContext';

export default function AppProviders({ children }) {
  return (
    <AuthProvider>
      <ConversationProvider>
        <CategoryProvider>
          {children}
        </CategoryProvider>
      </ConversationProvider>
    </AuthProvider>
  );
}

