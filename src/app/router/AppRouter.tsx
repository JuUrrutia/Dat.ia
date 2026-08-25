import React from 'react';
import { HashRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Header } from '../../components/layout/Header';
import { ToastContainer } from '../../components/shared/ToastContainer';
import { LoginPage } from '../../pages/LoginPage';
import { ChatDashboardPage } from '../../pages/ChatDashboardPage';
import { SettingsPage } from '../../pages/SettingsPage';
import { AdminPage } from '../../pages/AdminPage';

const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0B0F19] text-gray-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm">Cargando sesión...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="flex flex-col h-screen bg-[#0B0F19] text-gray-100 overflow-hidden font-sans">
      <Header />
      <main className="flex-1 overflow-hidden relative flex flex-col min-h-0">
        {children}
      </main>
      <ToastContainer />
    </div>
  );
};

export const AppRouter: React.FC = () => {
  const { user } = useAuth();

  return (
    <HashRouter>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/chat" replace /> : (
            <>
              <LoginPage />
              <ToastContainer />
            </>
          )}
        />
        <Route
          path="/chat"
          element={
            <ProtectedLayout>
              <ChatDashboardPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedLayout>
              <SettingsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedLayout>
              <AdminPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="*"
          element={<Navigate to={user ? "/chat" : "/login"} replace />}
        />
      </Routes>
    </HashRouter>
  );
};
