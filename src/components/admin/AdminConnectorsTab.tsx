import React, { useState } from 'react';
import { Database, Plus, Edit3, Trash2, RefreshCw, CheckCircle2, RotateCcw, Filter, UploadCloud, HardDrive, Sparkles } from 'lucide-react';
import { CorporateConnection } from '../../features/admin/services/connector_service';
import { DatabaseWizardModal } from './DatabaseWizardModal';
import { useAdminConnectors } from '../../features/admin/hooks/useAdminConnectors';

interface AdminConnectorsTabProps {
  connectors: CorporateConnection[];
  onOpenCreateModal: () => void;
  onOpenEditModal: (conn: CorporateConnection) => void;
  onDeleteConnector: (id: number, name: string) => void;
  onToggleActive: (id: number) => void;
  onResetDemoConnectors: () => void;
  onRefreshConnectors?: () => void;
}

export const AdminConnectorsTab: React.FC<AdminConnectorsTabProps> = ({
  connectors,
  onOpenCreateModal,
  onOpenEditModal,
  onDeleteConnector,
  onToggleActive,
  onResetDemoConnectors,
  onRefreshConnectors,
}) => {
  const {
    filterDbType,
    setFilterDbType,
    testingId,
    testResultsMap,
    handleTestCardConnection,
    filteredConnectors,
  } = useAdminConnectors(connectors);

  const [wizardMode, setWizardMode] = useState<'file' | 'remote'>('file');
  const [isWizardOpen, setIsWizardOpen] = useState(false);

  const handleOpenWizard = (mode: 'file' | 'remote' = 'file') => {
    setWizardMode(mode);
    setIsWizardOpen(true);
  };

  const getDbBadgeColor = (dbType: string) => {
    switch (dbType.toLowerCase()) {
      case 'sqlite':
        return 'bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-500/30';
      case 'postgresql':
        return 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30';
      case 'mysql':
        return 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30';
      case 'mssql':
        return 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30';
      default:
        return 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-500/30';
    }
  };

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-5 sm:p-6 border border-slate-200 dark:border-white/10 space-y-5 shadow-sm bg-white dark:bg-zinc-900/90 font-sans">
      {/* Header with Title and Action Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-dark-border/80 pb-4">
        <div>
          <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Database className="w-4 h-4 sm:w-5 sm:h-5 text-brand-600 dark:text-purple-400" />
            <span>Fuentes de Datos Corporativas Registradas</span>
            <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200 dark:bg-purple-500/15 dark:text-purple-300 dark:border-purple-500/30">
              {filteredConnectors.length} Conexiones
            </span>
          </h3>
          <p className="text-xs text-slate-600 dark:text-gray-400 mt-0.5">
            Conexiones operativas en modo solo lectura (<code>READ ONLY</code>) con soporte para SQLite, PostgreSQL, MySQL y SQL Server
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Filter by DB Type */}
          <div className="flex items-center space-x-1.5 text-xs bg-slate-50 dark:bg-dark-base/90 border border-slate-300 dark:border-dark-border rounded-xl px-3 py-2 shadow-xs">
            <Filter className="w-3.5 h-3.5 text-slate-500 dark:text-gray-400" />
            <label htmlFor="admin-filter-db-type" className="sr-only">
              Filtrar por motor de base de datos
            </label>
            <select
              id="admin-filter-db-type"
              aria-label="Filtrar por motor de base de datos"
              value={filterDbType}
              onChange={(e) => setFilterDbType(e.target.value)}
              className="bg-transparent text-slate-900 dark:text-white focus:outline-none text-xs pr-1 font-medium cursor-pointer"
            >
              <option value="ALL">Todos los Motores</option>
              <option value="sqlite">SQLite 3</option>
              <option value="postgresql">PostgreSQL</option>
              <option value="mssql">SQL Server</option>
              <option value="mysql">MySQL</option>
            </select>
          </div>

          {/* Action 1: Import Local File (SQLite / Excel / CSV) */}
          <button
            type="button"
            onClick={() => handleOpenWizard('file')}
            className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-bold px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-all glow-brand hover:scale-105 focus-visible:ring-2 focus-visible:ring-purple-500"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Importar Archivo (SQLite / Excel / CSV)</span>
          </button>

          {/* Action 2: Connect Remote DB (PostgreSQL / MSSQL / MySQL) */}
          <button
            type="button"
            onClick={() => handleOpenWizard('remote')}
            className="flex items-center space-x-1.5 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-card text-slate-800 dark:text-gray-200 border border-slate-300 dark:border-dark-border hover:border-brand-500/40 font-bold px-4 py-2 rounded-xl transition-all hover:scale-105 focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <Plus className="w-4 h-4 text-brand-600 dark:text-purple-400" />
            <span>Conectar BD Remota (Postgres / SQL Server)</span>
          </button>
        </div>
      </div>

      {/* Empty State */}
      {filteredConnectors.length === 0 && (
        <div className="text-center py-12 border border-dashed border-slate-300 dark:border-dark-border/80 rounded-2xl p-8 space-y-4 bg-slate-50/50 dark:bg-dark-base/50">
          <div className="w-12 h-12 rounded-full bg-brand-50 text-brand-600 dark:bg-purple-500/10 dark:text-purple-400 flex items-center justify-center mx-auto border border-brand-200 dark:border-purple-500/20 shadow-xs">
            <Database className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">No hay fuentes de datos registradas para este filtro</h4>
            <p className="text-xs text-slate-600 dark:text-gray-400 max-w-sm mx-auto">
              Importa un archivo SQLite, Excel (.xlsx) o CSV (.csv), o registra una conexión remota a PostgreSQL, SQL Server o MySQL.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={onResetDemoConnectors}
              className="flex items-center space-x-1.5 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-card text-slate-700 dark:text-gray-300 border border-slate-300 dark:border-dark-border px-4 py-2 rounded-xl transition-colors font-semibold"
            >
              <RotateCcw className="w-3.5 h-3.5 text-brand-600 dark:text-purple-400" />
              <span>Restablecer Fuentes Demo</span>
            </button>
            <button
              type="button"
              onClick={() => handleOpenWizard('file')}
              className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-bold px-4 py-2 rounded-xl transition-all shadow-lg shadow-purple-600/30"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Iniciar Asistente / Wizard BD</span>
            </button>
            <button
              type="button"
              onClick={() => handleOpenWizard('file')}
              className="flex items-center space-x-1.5 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-card text-slate-800 dark:text-gray-200 border border-slate-300 dark:border-dark-border font-bold px-4 py-2 rounded-xl transition-colors"
            >
              <UploadCloud className="w-3.5 h-3.5 text-brand-600 dark:text-purple-400" />
              <span>Importar Archivo</span>
            </button>
          </div>
        </div>
      )}

      {/* Connectors 3-Column Responsive Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
        {filteredConnectors.map((c) => {
          const testRes = testResultsMap[c.id];
          const badgeStyle = getDbBadgeColor(c.db_type);

          return (
            <div
              key={c.id}
              className="glass-card-interactive p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-white/10 flex flex-col justify-between space-y-4 shadow-sm bg-white dark:bg-zinc-900/90 group"
            >
              <div className="space-y-3">
                {/* Card Title & Type Badges */}
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1 min-w-0">
                    <div className="font-bold text-slate-900 dark:text-white text-sm truncate group-hover:text-brand-600 dark:group-hover:text-purple-300 transition-colors">
                      {c.name}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={`text-[10px] border px-2 py-0.5 rounded-md font-mono uppercase tracking-wider font-bold ${badgeStyle}`}>
                        {c.db_type}
                      </span>
                      {c.is_uploaded && (
                        <span className="text-[9px] bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-500/15 dark:text-cyan-300 dark:border-cyan-500/30 px-1.5 py-0.5 rounded font-semibold flex items-center gap-1">
                          <HardDrive className="w-2.5 h-2.5" />
                          Importado
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions Header */}
                  <div className="flex items-center space-x-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => onOpenEditModal(c)}
                      title="Editar Conexión"
                      aria-label={`Editar conexión ${c.name}`}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-slate-100 dark:text-gray-400 dark:hover:text-purple-300 dark:hover:bg-purple-500/15 border border-transparent hover:border-brand-500/30 transition-all focus-visible:ring-2 focus-visible:ring-brand-500"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => onDeleteConnector(c.id, c.name)}
                      title="Eliminar Conexión"
                      aria-label={`Eliminar conexión ${c.name}`}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:text-gray-400 dark:hover:text-rose-400 dark:hover:bg-rose-500/15 border border-transparent hover:border-rose-500/30 transition-all focus-visible:ring-2 focus-visible:ring-rose-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Connection Meta Details */}
                <div className="bg-slate-50 dark:bg-dark-base/70 p-2.5 rounded-xl border border-slate-200 dark:border-dark-border/60 text-xs space-y-1 font-mono">
                  <div className="text-slate-700 dark:text-gray-400 text-[11px] truncate" title={c.host}>
                    <span className="text-slate-500 dark:text-gray-500 uppercase font-sans font-bold">Host: </span>
                    <span className="text-cyan-700 dark:text-cyan-300 font-semibold">{c.host}{c.port ? `:${c.port}` : ''}</span>
                  </div>
                  <div className="text-slate-700 dark:text-gray-400 text-[11px] truncate" title={c.database_name}>
                    <span className="text-slate-500 dark:text-gray-500 uppercase font-sans font-bold">BD: </span>
                    <span className="text-indigo-700 dark:text-indigo-300 font-semibold">{c.database_name}</span>
                  </div>
                </div>
              </div>

              {/* Bottom Actions & Status Toggle */}
              <div className="space-y-2.5 pt-2 border-t border-slate-200 dark:border-dark-border/60">
                <div className="flex items-center justify-between text-xs">
                  <button
                    type="button"
                    onClick={() => onToggleActive(c.id)}
                    className="flex items-center space-x-2 group focus:outline-none"
                  >
                    {c.is_active ? (
                      <span className="relative flex h-2.5 w-2.5 shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                      </span>
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-400 dark:bg-gray-500 shrink-0" />
                    )}
                    <span className={`text-[11px] font-semibold ${c.is_active ? 'text-emerald-700 dark:text-emerald-400' : 'text-slate-500 dark:text-gray-400'}`}>
                      {c.is_active ? 'Activa para Consultas' : 'Inactiva (Deshabilitada)'}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTestCardConnection(c)}
                    disabled={testingId === c.id}
                    className="flex items-center space-x-1.5 text-xs text-brand-700 dark:text-purple-300 hover:text-brand-800 dark:hover:text-white bg-brand-50 hover:bg-brand-100 dark:bg-purple-500/10 dark:hover:bg-purple-500/20 border border-brand-200 dark:border-purple-500/30 px-3 py-1 rounded-lg transition-all font-semibold"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-brand-600 dark:text-purple-400 ${testingId === c.id ? 'animate-spin' : ''}`} />
                    <span>{testingId === c.id ? 'Probando...' : 'Probar'}</span>
                  </button>
                </div>

                {testRes && (
                  <div
                    className={`p-2 rounded-xl border text-[11px] flex items-center space-x-2 animate-fadeIn ${
                      testRes.success
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-300'
                        : 'bg-rose-50 border-rose-200 text-rose-800 dark:bg-rose-500/10 dark:border-rose-500/30 dark:text-rose-300'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                    <span className="truncate font-medium">{testRes.message} ({testRes.latency_ms} ms)</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Database Installation Wizard Modal */}
      <DatabaseWizardModal
        isOpen={isWizardOpen}
        initialMode={wizardMode}
        onClose={() => setIsWizardOpen(false)}
        onSuccess={() => {
          if (onRefreshConnectors) {
            onRefreshConnectors();
          }
        }}
      />
    </div>
  );
};
