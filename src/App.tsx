import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/layout/Header';
import { LoginPage } from './pages/LoginPage';
import { ChatDashboardPage } from './pages/ChatDashboardPage';
import { SettingsPage } from './pages/SettingsPage';
import { AdminPage } from './pages/AdminPage';

const MainAppContent: React.FC = () => {
  const { user, activePage } = useAuth();

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="flex flex-col h-screen bg-[#0B0F19] text-gray-100 overflow-hidden font-sans">
      <Header />
      <main className="flex-1 overflow-hidden relative">
        {activePage === 'dashboard' && <ChatDashboardPage />}
        {activePage === 'settings' && <SettingsPage />}
        {activePage === 'admin' && <AdminPage />}
      </main>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
}

export default App;
