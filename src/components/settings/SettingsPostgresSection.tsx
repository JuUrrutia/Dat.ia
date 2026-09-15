import React from 'react';
import { Database, RefreshCw, CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react';

interface SettingsPostgresSectionProps {
  pgHost: string;
  pgPort: number;
  pgDb: string;
  testingPG: boolean;
  pgStatus: { success: boolean; message: string } | null;
  onPgHostChange: (val: string) => void;
  onPgPortChange: (val: number) => void;
  onPgDbChange: (val: string) => void;
  onTestPG: () => void;
}

export const SettingsPostgresSection: React.FC<SettingsPostgresSectionProps> = ({
  pgHost,
  pgPort,
  pgDb,
  testingPG,
  pgStatus,
  onPgHostChange,
  onPgPortChange,
  onPgDbChange,
  onTestPG,
}) => {
  return (
    <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4 shadow-xl font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dark-border/80 pb-3.5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-600/20 to-cyan-600/20 text-blue-400 border border-blue-500/30 shadow-md">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span>Base de Metadatos & Logs (PostgreSQL)</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30">
                Audit & Schema DB
              </span>
            </h3>
            <p className="text-[11px] text-gray-400">Almacenamiento persistente de logs de auditoría y diccionario semántico</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onTestPG}
          disabled={testingPG}
          className="flex items-center justify-center space-x-1.5 text-xs font-semibold bg-dark-base/80 hover:bg-dark-card text-blue-300 border border-blue-500/30 hover:border-blue-500/60 px-3.5 py-2 rounded-xl transition-all shadow-sm focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${testingPG ? 'animate-spin' : ''}`} />
          <span>{testingPG ? 'Verificando BD...' : 'Probar Conexión PG'}</span>
        </button>
      </div>

      {/* Grid Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div>
          <label htmlFor="pg-host-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            Servidor Host
          </label>
          <input
            id="pg-host-input"
            type="text"
            value={pgHost}
            onChange={(e) => onPgHostChange(e.target.value)}
            aria-label="Servidor Host"
            className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-brand-300 font-mono focus:outline-none focus:border-blue-500 transition-colors shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="pg-port-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            Puerto
          </label>
          <input
            id="pg-port-input"
            type="number"
            value={pgPort}
            onChange={(e) => {
              const val = e.currentTarget.valueAsNumber;
              onPgPortChange(Number.isFinite(val) ? val : 5432);
            }}
            aria-label="Puerto de la base de datos"
            className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-brand-300 font-mono focus:outline-none focus:border-blue-500 transition-colors shadow-inner"
          />
        </div>

        <div>
          <label htmlFor="pg-db-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            Nombre BD
          </label>
          <input
            id="pg-db-input"
            type="text"
            value={pgDb}
            onChange={(e) => onPgDbChange(e.target.value)}
            aria-label="Nombre de la Base de Datos"
            className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-brand-300 font-mono focus:outline-none focus:border-blue-500 transition-colors shadow-inner"
          />
        </div>
      </div>

      {/* Security note */}
      <div className="flex items-center space-x-2 text-[10px] text-gray-400 bg-dark-base/40 px-3 py-1.5 rounded-lg border border-dark-border/60">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
        <span>Conexión segura cifrada con TLS y roles aislados de sólo lectura para auditorías.</span>
      </div>

      {pgStatus && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
            pgStatus.success
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {pgStatus.success ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" /> : <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />}
          <span className="font-medium">{pgStatus.message}</span>
        </div>
      )}
    </div>
  );
};
