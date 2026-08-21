import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSystemHealth } from '../../hooks/useSystemHealth';
import {
  Settings,
  ShieldAlert,
  LogOut,
  WifiOff,
  Sparkles,
  LayoutDashboard,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Database,
  Cpu,
  RefreshCw,
  X,
  Server,
} from 'lucide-react';

export const Header: React.FC = () => {
  const { user, activePage, setActivePage, logout } = useAuth();
  const { status, details, lastChecked, isLoading, refetch } = useSystemHealth();
  const [isHealthPopoverOpen, setIsHealthPopoverOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsHealthPopoverOpen(false);
      }
    };
    if (isHealthPopoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isHealthPopoverOpen]);

  if (!user) return null;

  const getStatusBadgeUI = () => {
    switch (status) {
      case 'CRITICO':
        return {
          bg: 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20',
          icon: <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />,
          label: 'LLM No Disponible',
        };
      case 'DEGRADADO':
        return {
          bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400 hover:bg-amber-500/20',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
          label: 'Sistema Degradado',
        };
      case 'OPERATIVO':
      default:
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20',
          icon: <WifiOff className="w-3.5 h-3.5 text-emerald-400" />,
          label: '100% Offline Standalone',
        };
    }
  };

  const badgeUI = getStatusBadgeUI();

  return (
    <header className="h-16 border-b border-dark-border bg-dark-surface/90 backdrop-blur-md px-6 flex items-center justify-between z-20 relative">
      {/* Brand & Offline / Dynamic Health Status Badge */}
      <div className="flex items-center space-x-4">
        <button
          type="button"
          className="flex items-center space-x-3 text-left focus:outline-none"
          onClick={() => setActivePage('dashboard')}
        >
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

        {/* Dynamic Health Status Indicator with Popover */}
        <div className="relative hidden md:block" ref={popoverRef}>
          <button
            type="button"
            onClick={() => setIsHealthPopoverOpen((prev) => !prev)}
            aria-label="Ver estado de salud del sistema"
            aria-expanded={isHealthPopoverOpen}
            className={`flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-medium transition-colors shadow-sm ${badgeUI.bg}`}
          >
            {badgeUI.icon}
            <span>{badgeUI.label}</span>
          </button>

          {/* Health Popover Details */}
          {isHealthPopoverOpen && (
            <div className="absolute left-0 mt-2 w-80 rounded-2xl bg-dark-surface border border-dark-border shadow-2xl p-4 z-50 space-y-3.5 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-dark-border pb-2.5">
                <div>
                  <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-brand-400" />
                    Estado General del Sistema
                  </h4>
                  <span className="text-[10px] text-gray-400">
                    Último chequeo: {lastChecked ? lastChecked.toLocaleTimeString() : 'Reciente'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsHealthPopoverOpen(false)}
                  aria-label="Cerrar detalles de salud"
                  className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Component breakdown */}
              <div className="space-y-2 text-xs">
                {/* 1. LLM Engine */}
                <div className="p-2.5 rounded-xl bg-dark-base border border-dark-border flex items-center justify-between">
                  <div className="flex items-center space-x-2 min-w-0">
                    <Cpu className="w-4 h-4 text-purple-400 shrink-0" />
                    <div className="truncate">
                      <div className="text-white font-medium truncate">
                        {details?.llm_engine.name || 'Motor LLM'}
                      </div>
                      <div className="text-[10px] text-gray-400">
                        {details?.llm_engine.latency_ms || 0} ms
                      </div>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${
                      details?.llm_engine.status === 'OPERATIVO'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    }`}
                  >
                    {details?.llm_engine.status || 'OPERATIVO'}
                  </span>
                </div>

                {/* 2. Metadata Database */}
                <div className="p-2.5 rounded-xl bg-dark-base border border-dark-border flex items-center justify-between">
                  <div className="flex items-center space-x-2 min-w-0">
                    <Database className="w-4 h-4 text-brand-400 shrink-0" />
                    <div className="truncate">
                      <div className="text-white font-medium truncate">
                        {details?.metadata_db.name || 'Base Metadatos (Datia)'}
                      </div>
                      <div className="text-[10px] text-gray-400">
                        {details?.metadata_db.latency_ms || 0} ms
                      </div>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${
                      details?.metadata_db.status === 'OPERATIVO'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {details?.metadata_db.status || 'OPERATIVO'}
                  </span>
                </div>

                {/* 3. Corporate Database Connectors */}
                {details?.corporate_connectors && details.corporate_connectors.length > 0 && (
                  <div className="space-y-1 pt-1">
                    <div className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">
                      Fuentes Corporativas Activas ({details.healthy_connectors_count}/{details.total_active_connectors})
                    </div>
                    <div className="max-h-28 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                      {details.corporate_connectors.map((c) => (
                        <div
                          key={c.name}
                          className="p-2 rounded-lg bg-dark-base/60 border border-dark-border/60 flex items-center justify-between text-[11px]"
                        >
                          <span className="text-gray-200 truncate">{c.name}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[9px] font-medium border shrink-0 ${
                              c.status === 'OPERATIVO'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}
                          >
                            {c.latency_ms} ms
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Refresh Action */}
              <div className="pt-2 border-t border-dark-border flex justify-end">
                <button
                  type="button"
                  onClick={() => refetch()}
                  disabled={isLoading}
                  className="flex items-center space-x-1 text-[11px] text-brand-400 hover:text-brand-300 transition-colors"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
                  <span>Verificar ahora</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Navigation Links */}
      <nav className="flex items-center space-x-1 bg-dark-base/60 p-1 rounded-xl border border-dark-border">
        <button
          type="button"
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
          type="button"
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
            type="button"
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
          type="button"
          onClick={logout}
          title="Cerrar Sesión"
          aria-label="Cerrar Sesión"
          className="p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
