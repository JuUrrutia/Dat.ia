import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../features/auth/context/AuthContext';
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
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { status, details, lastChecked, isLoading, refetch } = useSystemHealth();
  const [isHealthPopoverOpen, setIsHealthPopoverOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  const activePath = location.pathname;

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
    <header className="h-16 border-b border-dark-border/80 bg-dark-surface/95 backdrop-blur-xl px-3 sm:px-6 flex items-center justify-between z-30 relative select-none font-sans">
      {/* Brand & Offline / Dynamic Health Status Badge */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        <button
          type="button"
          aria-label="Ir a Dashboard de DATIA"
          className="flex items-center space-x-2.5 sm:space-x-3 text-left group rounded-xl p-1 transition-all focus-visible:ring-2 focus-visible:ring-brand-500"
          onClick={() => {
            navigate('/chat');
            setIsMobileMenuOpen(false);
          }}
        >
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-brand-500/25 shrink-0 group-hover:scale-105 transition-transform">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div className="truncate">
            <h1 className="text-xs sm:text-base font-bold text-white tracking-tight flex items-center gap-1.5 sm:gap-2">
              <span>DATIA</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/30">
                IA Local
              </span>
            </h1>
            <p className="text-[10px] sm:text-xs text-gray-400 font-medium hidden xs:block truncate">
              Democratización de Datos Corporativos
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
      <nav className="hidden md:flex items-center space-x-1.5 bg-dark-base/80 p-1.5 rounded-2xl border border-dark-border/80 shadow-inner">
        <button
          type="button"
          aria-current={activePath === '/chat' || activePath === '/' ? 'page' : undefined}
          onClick={() => navigate('/chat')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activePath === '/chat' || activePath === '/'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/35 glow-brand'
              : 'text-gray-300 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Dashboard & Chat</span>
        </button>

        <button
          type="button"
          aria-current={activePath === '/settings' ? 'page' : undefined}
          onClick={() => navigate('/settings')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activePath === '/settings'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/35 glow-brand'
              : 'text-gray-300 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <Settings className="w-4 h-4" />
          <span>Opciones</span>
        </button>

        {user.is_admin && (
          <button
            type="button"
            aria-current={activePath === '/admin' ? 'page' : undefined}
            onClick={() => navigate('/admin')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activePath === '/admin'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/35'
                : 'text-gray-300 hover:text-white hover:bg-dark-card/60'
            }`}
          >
            <ShieldAlert className="w-4 h-4 text-purple-300" />
            <span>Gobernanza RBAC</span>
          </button>
        )}
      </nav>

      {/* Right Actions & Mobile Hamburger */}
      <div className="flex items-center space-x-2 sm:space-x-4">
        <div className="text-right hidden sm:block">
          <div className="text-xs font-bold text-white tracking-tight">{user.username}</div>
          <div className="text-[10px] font-semibold text-brand-300 bg-brand-500/15 px-2.5 py-0.5 rounded-full border border-brand-500/30 inline-block mt-0.5">
            {user.role_name || (user.is_admin ? 'Super Administrador' : 'Usuario')}
          </div>
        </div>

        <button
          type="button"
          onClick={logout}
          title="Cerrar Sesión Segura"
          aria-label="Cerrar Sesión Segura"
          className="hidden sm:flex p-2.5 rounded-xl text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition-all focus-visible:ring-2 focus-visible:ring-rose-500"
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
                    navigate('/chat');
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                    activePath === '/chat' || activePath === '/'
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
                    navigate('/settings');
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                    activePath === '/settings'
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
                      navigate('/admin');
                      setIsMobileMenuOpen(false);
                    }}
                    className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-colors ${
                      activePath === '/admin'
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
