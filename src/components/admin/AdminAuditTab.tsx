import React from 'react';
import {
  ShieldCheck,
  Download,
  RefreshCw,
  Database,
  AlertTriangle,
  Eye,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { AuditFilters } from './AuditFilters';
import { AuditInspectorModal, AuditStatusBadge } from './AuditInspectorModal';
import { useAdminAudit } from '../../features/admin/hooks/useAdminAudit';

export const AdminAuditTab: React.FC = () => {
  const {
    logs,
    total,
    page,
    totalPages,
    loading,
    exporting,
    error,
    startDate,
    endDate,
    filterUsername,
    filterDatabase,
    filterStatus,
    selectedLog,
    setSelectedLog,
    setStartDate,
    setEndDate,
    setFilterUsername,
    setFilterDatabase,
    setFilterStatus,
    fetchLogs,
    handleFilterSubmit,
    handleClearFilters,
    handleExportCsv,
  } = useAdminAudit();

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-200 dark:border-white/10 space-y-6 bg-white dark:bg-zinc-900/90 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> Registro de Auditoría & Trazabilidad de Consultas
          </h3>
          <p className="text-xs text-slate-600 dark:text-gray-400">
            Monitoreo en tiempo real de preguntas analíticas, SQL validado por AST Guardrail y estado de ejecución
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => fetchLogs(page)}
            disabled={loading}
            aria-label="Refrescar logs"
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 dark:bg-dark-card dark:hover:bg-dark-border dark:text-gray-300 dark:hover:text-white transition-colors border border-slate-200 dark:border-dark-border cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exporting || logs.length === 0}
            className="flex items-center space-x-1.5 text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-dark-card dark:hover:bg-dark-border dark:text-emerald-400 font-semibold px-4 py-2 rounded-xl border border-emerald-200 dark:border-emerald-500/30 transition-colors shadow-xs cursor-pointer"
          >
            {exporting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Exportar CSV</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <AuditFilters
        startDate={startDate}
        endDate={endDate}
        filterUsername={filterUsername}
        filterDatabase={filterDatabase}
        filterStatus={filterStatus}
        loading={loading}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onUsernameChange={setFilterUsername}
        onDatabaseChange={setFilterDatabase}
        onStatusChange={setFilterStatus}
        onSubmit={handleFilterSubmit}
        onClear={handleClearFilters}
      />

      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Logs Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-dark-base border-b border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Fecha (UTC)</th>
              <th className="px-4 py-3">Usuario & Rol</th>
              <th className="px-4 py-3">Pregunta / Prompt</th>
              <th className="px-4 py-3">Estado AST</th>
              <th className="px-4 py-3">Base de Datos</th>
              <th className="px-4 py-3">Latencia</th>
              <th className="px-4 py-3 text-right">Detalles</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-dark-border text-slate-800 dark:text-gray-200 bg-white dark:bg-transparent">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-600 dark:text-gray-400">
                  <div className="flex items-center justify-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-600 dark:text-emerald-400" />
                    <span>Cargando registros de auditoría...</span>
                  </div>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500 dark:text-gray-400">
                  No se encontraron consultas registradas con los filtros seleccionados.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-dark-card/50 transition-colors">
                  <td className="px-4 py-3 text-slate-600 dark:text-gray-400 font-mono text-[11px] whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900 dark:text-white">{log.username}</div>
                    <div className="text-[10px] text-slate-500 dark:text-gray-400">{log.user_role || 'Sin Rol'}</div>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate text-slate-700 dark:text-gray-300" title={log.question_prompt}>
                    {log.question_prompt}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <AuditStatusBadge status={log.validation_status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-gray-400 flex items-center space-x-1.5 whitespace-nowrap">
                    <Database className="w-3.5 h-3.5 text-slate-400 dark:text-gray-500" />
                    <span>{log.target_database || 'SQLite Demo'}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-gray-400 font-mono whitespace-nowrap">
                    {log.execution_time_ms} ms
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => setSelectedLog(log)}
                      aria-label={`Ver detalles del log ID ${log.id}`}
                      className="p-1.5 rounded-lg bg-slate-100 hover:bg-emerald-50 text-slate-600 hover:text-emerald-700 border border-slate-200 hover:border-emerald-300 dark:bg-dark-card dark:hover:bg-emerald-500/20 dark:text-gray-400 dark:hover:text-emerald-300 dark:border-dark-border dark:hover:border-emerald-500/30 transition-colors cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-gray-400 pt-2">
        <div>
          Mostrando {logs.length} de {total} eventos registrados (Página {page} de {totalPages})
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => fetchLogs(page - 1)}
            disabled={page <= 1 || loading}
            aria-label="Página anterior"
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 disabled:opacity-40 disabled:pointer-events-none text-slate-700 hover:text-slate-900 dark:bg-dark-card dark:hover:bg-dark-border dark:text-gray-300 dark:hover:text-white transition-colors border border-slate-200 dark:border-dark-border cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Anterior</span>
          </button>
          <button
            type="button"
            onClick={() => fetchLogs(page + 1)}
            disabled={page >= totalPages || loading}
            aria-label="Página siguiente"
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 disabled:opacity-40 disabled:pointer-events-none text-slate-700 hover:text-slate-900 dark:bg-dark-card dark:hover:bg-dark-border dark:text-gray-300 dark:hover:text-white transition-colors border border-slate-200 dark:border-dark-border cursor-pointer"
          >
            <span>Siguiente</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* SQL & Traceability Inspector Modal */}
      <AuditInspectorModal
        log={selectedLog}
        onClose={() => setSelectedLog(null)}
      />
    </div>
  );
};
