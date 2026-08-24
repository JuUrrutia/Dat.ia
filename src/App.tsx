import React from 'react';
import { SettingsProvider } from './features/settings/context/SettingsContext';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { AppRouter } from './app/router/AppRouter';

export function App() {
  return (
    <NotificationProvider>
      <SettingsProvider>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </SettingsProvider>
    </NotificationProvider>
  );
}

export default App;
