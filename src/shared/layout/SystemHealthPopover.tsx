import React, { useRef, useEffect } from 'react';
import {
  Server,
  X,
  Cpu,
  Database,
  RefreshCw,
  AlertTriangle,
  AlertOctagon,
  WifiOff,
} from 'lucide-react';
import { SystemHealthResponse, ComponentHealth } from '../../types';

interface SystemHealthPopoverProps {
  status: 'OPERATIVO' | 'DEGRADADO' | 'CRITICO';
  details: SystemHealthResponse | null;
  lastChecked: Date | null;
  isLoading: boolean;
  refetch: () => void;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
}

export const SystemHealthPopover: React.FC<SystemHealthPopoverProps> = ({
  status,
  details,
  lastChecked,
  isLoading,
  refetch,
  isOpen,
  onToggle,
  onClose,
}) => {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

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
      default: {
        const prov = details?.llm_engine?.details?.provider;
        const provLabel = prov === 'llama_cpp' ? 'llama.cpp' : prov === 'ollama' ? 'Ollama' : 'IA Local';
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20',
          icon: <WifiOff className="w-3.5 h-3.5 text-emerald-400" />,
          label: `IA Local Activa (${provLabel})`,
        };
      }
    }
  };

  const badgeUI = getStatusBadgeUI();

  return (
    <div className="relative hidden md:block" ref={popoverRef}>
      <button
        type="button"
        onClick={onToggle}
        aria-label="Ver estado de salud del sistema"
        aria-expanded={isOpen}
        className={`flex items-center space-x-2 px-3 py-1 rounded-full border text-xs font-medium transition-colors shadow-sm ${badgeUI.bg}`}
      >
        {badgeUI.icon}
        <span>{badgeUI.label}</span>
      </button>

      {/* Health Popover Details */}
      {isOpen && (
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
              onClick={onClose}
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
                  {details.corporate_connectors.map((c: ComponentHealth) => (
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
              className="flex items-center space-x-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Actualizar Estado</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
