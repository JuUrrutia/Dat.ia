import React from 'react';
import { Database, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

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
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      <div className="flex items-center justify-between border-b border-dark-border pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Base de Datos de Metadatos y Diccionario Semántico</h3>
            <p className="text-xs text-gray-400">Servidor PostgreSQL de almacenamiento de logs de auditoría y esquemas</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onTestPG}
          disabled={testingPG}
          className="flex items-center space-x-1.5 text-xs bg-dark-card hover:bg-dark-border text-blue-400 border border-blue-500/30 px-3.5 py-2 rounded-xl transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testingPG ? 'animate-spin' : ''}`} />
          <span>{testingPG ? 'Verificando BD...' : 'Probar Conexión PostgreSQL'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="pg-host-input" className="block text-xs font-semibold text-gray-300 mb-1.5">Servidor Host</label>
          <input
            id="pg-host-input"
            type="text"
            value={pgHost}
            onChange={(e) => onPgHostChange(e.target.value)}
            aria-label="Servidor Host"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
          />
        </div>

        <div>
          <label htmlFor="pg-port-input" className="block text-xs font-semibold text-gray-300 mb-1.5">Puerto</label>
          <input
            id="pg-port-input"
            type="number"
            value={pgPort}
            onChange={(e) => {
              const val = e.currentTarget.valueAsNumber;
              onPgPortChange(Number.isFinite(val) ? val : 5432);
            }}
            aria-label="Puerto de la base de datos"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
          />
        </div>

        <div>
          <label htmlFor="pg-db-input" className="block text-xs font-semibold text-gray-300 mb-1.5">Nombre BD</label>
          <input
            id="pg-db-input"
            type="text"
            value={pgDb}
            onChange={(e) => onPgDbChange(e.target.value)}
            aria-label="Nombre de la Base de Datos"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
          />
        </div>
      </div>

      {pgStatus && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
            pgStatus.success
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
          }`}
        >
          {pgStatus.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{pgStatus.message}</span>
        </div>
      )}
    </div>
  );
};
