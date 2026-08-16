import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Bot, Settings, ShieldAlert, LogOut, Database, WifiOff, Sparkles, LayoutDashboard } from 'lucide-react';

export const Header: React.FC = () => {
  const { user, activePage, setActivePage, logout } = useAuth();

  if (!user) return null;

  return (
    <header className="h-16 border-b border-dark-border bg-dark-surface/90 backdrop-blur-md px-6 flex items-center justify-between z-20">
      {/* Brand & Offline Status Badge */}
      <div className="flex items-center space-x-4">
        <button type="button" className="flex items-center space-x-3 text-left focus:outline-none" onClick={() => setActivePage('dashboard')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
              Democratización de Datos
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-normal">
                IA Local
              </span>
            </h1>
            <p className="text-xs text-gray-400">Soberanía de Datos Corporativos</p>
          </div>
        </button>

        <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <WifiOff className="w-3.5 h-3.5" />
          <span>100% Offline Standalone</span>
        </div>
      </div>

      {/* Main Navigation Links */}
      <nav className="flex items-center space-x-1 bg-dark-base/60 p-1 rounded-xl border border-dark-border">
        <button
          onClick={() => setActivePage('dashboard')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
            activePage === 'dashboard'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Dashboard & Chat</span>
        </button>

        <button
          onClick={() => setActivePage('settings')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
            activePage === 'settings'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <Settings className="w-4 h-4" />
          <span>Opciones</span>
        </button>

        {user.is_admin && (
          <button
            onClick={() => setActivePage('admin')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
              activePage === 'admin'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Administración RBAC</span>
          </button>
        )}
      </nav>

      {/* User Profile & Actions */}
      <div className="flex items-center space-x-4">
        <div className="text-right hidden sm:block">
          <div className="text-xs font-semibold text-gray-200">{user.username}</div>
          <div className="text-[10px] text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20 inline-block mt-0.5">
            {user.role_name || (user.is_admin ? 'Super Administrador' : 'Usuario')}
          </div>
        </div>

        <button
          onClick={logout}
          title="Cerrar Sesión"
          className="p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
