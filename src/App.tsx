import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { ToastContainer } from './components/shared/ToastContainer';
import { Header } from './components/layout/Header';
import { LoginPage } from './pages/LoginPage';
import { ChatDashboardPage } from './pages/ChatDashboardPage';
import { SettingsPage } from './pages/SettingsPage';
import { AdminPage } from './pages/AdminPage';

const MainAppContent: React.FC = () => {
  const { user, activePage } = useAuth();

  if (!user) {
    return (
      <>
        <LoginPage />
        <ToastContainer />
      </>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#0B0F19] text-gray-100 overflow-hidden font-sans">
      <Header />
      <main className="flex-1 overflow-hidden relative flex flex-col min-h-0">
        {activePage === 'dashboard' && <ChatDashboardPage />}
        {activePage === 'settings' && <SettingsPage />}
        {activePage === 'admin' && <AdminPage />}
      </main>
      <ToastContainer />
    </div>
  );
};

export function App() {
  return (
    <NotificationProvider>
      <AuthProvider>
        <MainAppContent />
      </AuthProvider>
    </NotificationProvider>
  );
}

export default App;
