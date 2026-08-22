import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSystemHealth } from '../../hooks/useSystemHealth';
import {
  Settings,
  ShieldAlert,
  LogOut,
  Sparkles,
  LayoutDashboard,
  Menu,
  X,
} from 'lucide-react';
import { SystemHealthPopover } from './SystemHealthPopover';

export const Header: React.FC = () => {
  const { user, activePage, setActivePage, logout } = useAuth();
  const { status, details, lastChecked, isLoading, refetch } = useSystemHealth();
  const [isHealthPopoverOpen, setIsHealthPopoverOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  // Close mobile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(e.target as Node)) {
        setIsMobileMenuOpen(false);
      }
    };
    if (isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMobileMenuOpen]);

  if (!user) return null;

  return (
    <header className="h-16 border-b border-dark-border bg-dark-surface/90 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between z-30 relative select-none">
      {/* Brand & Offline / Dynamic Health Status Badge */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        <button
          type="button"
          className="flex items-center space-x-2.5 sm:space-x-3 text-left focus:outline-none"
          onClick={() => {
            setActivePage('dashboard');
            setIsMobileMenuOpen(false);
          }}
        >
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-brand-500/20 shrink-0">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div className="truncate">
            <h1 className="text-xs sm:text-base font-semibold text-white tracking-tight flex items-center gap-1.5 sm:gap-2">
              <span>DATIA</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-normal">
                IA Local
              </span>
            </h1>
            <p className="text-[10px] sm:text-xs text-gray-400 hidden xs:block truncate">
              Democratización de Datos
            </p>
          </div>
        </button>

        {/* Dynamic Health Status Indicator with Popover */}
        <SystemHealthPopover
          status={status}
          details={details}
          lastChecked={lastChecked}
          isLoading={isLoading}
          refetch={refetch}
          isOpen={isHealthPopoverOpen}
          onToggle={() => setIsHealthPopoverOpen((prev) => !prev)}
          onClose={() => setIsHealthPopoverOpen(false)}
        />
      </div>

      {/* Desktop Main Navigation Links */}
      <nav className="hidden md:flex items-center space-x-1 bg-dark-base/60 p-1 rounded-xl border border-dark-border">
        <button
          type="button"
          onClick={() => setActivePage('dashboard')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors ${
            activePage === 'dashboard'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Dashboard & Chat</span>
        </button>

        <button
          type="button"
          onClick={() => setActivePage('settings')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors ${
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
            type="button"
            onClick={() => setActivePage('admin')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors ${
              activePage === 'admin'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                : 'text-gray-400 hover:text-white hover:bg-dark-card/50'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Gobernanza RBAC</span>
          </button>
        )}
      </nav>

      {/* Right Actions & Mobile Hamburger */}
      <div className="flex items-center space-x-2 sm:space-x-4">
        <div className="text-right hidden sm:block">
          <div className="text-xs font-semibold text-gray-200">{user.username}</div>
          <div className="text-[10px] text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20 inline-block mt-0.5">
            {user.role_name || (user.is_admin ? 'Super Administrador' : 'Usuario')}
          </div>
        </div>

        <button
          type="button"
          onClick={logout}
          title="Cerrar Sesión"
          aria-label="Cerrar Sesión"
          className="hidden sm:flex p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>

        {/* Mobile Hamburger Button */}
        <div className="md:hidden relative" ref={mobileMenuRef}>
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            aria-label="Abrir menú de navegación"
            className="p-2 rounded-xl bg-dark-base border border-dark-border text-gray-300 hover:text-white hover:border-brand-500/40 transition-colors"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5 text-brand-400" /> : <Menu className="w-5 h-5" />}
          </button>

          {/* Mobile Drawer Dropdown */}
          {isMobileMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-dark-surface border border-dark-border shadow-2xl p-3 z-50 space-y-2 animate-fadeIn">
              {/* User Info on Mobile */}
              <div className="p-3 rounded-xl bg-dark-base border border-dark-border">
                <div className="text-xs font-bold text-white">{user.username}</div>
                <div className="text-[10px] text-brand-400 mt-0.5">
                  {user.role_name || (user.is_admin ? 'Super Administrador' : 'Usuario')}
                </div>
              </div>

              {/* Navigation Links */}
              <div className="space-y-1 pt-1 border-t border-dark-border">
                <button
                  type="button"
                  onClick={() => {
                    setActivePage('dashboard');
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                    activePage === 'dashboard'
                      ? 'bg-brand-600 text-white'
                      : 'text-gray-300 hover:bg-dark-card'
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Dashboard & Chat</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setActivePage('settings');
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                    activePage === 'settings'
                      ? 'bg-brand-600 text-white'
                      : 'text-gray-300 hover:bg-dark-card'
                  }`}
                >
                  <Settings className="w-4 h-4" />
                  <span>Opciones & Configuración</span>
                </button>

                {user.is_admin && (
                  <button
                    type="button"
                    onClick={() => {
                      setActivePage('admin');
                      setIsMobileMenuOpen(false);
                    }}
                    className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                      activePage === 'admin'
                        ? 'bg-purple-600 text-white'
                        : 'text-gray-300 hover:bg-dark-card'
                    }`}
                  >
                    <ShieldAlert className="w-4 h-4" />
                    <span>Gobernanza RBAC & BD</span>
                  </button>
                )}
              </div>

              {/* Logout Button */}
              <div className="pt-2 border-t border-dark-border">
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full flex items-center space-x-2 px-3 py-2 rounded-xl text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Cerrar Sesión</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
