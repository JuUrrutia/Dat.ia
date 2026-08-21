import React, { useState, useEffect, useCallback } from 'react';
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
import { auditService } from '../../services/audit_service';
import { AuditLog, AuditFilterParams } from '../../types';
import { AuditFilters } from './AuditFilters';
import { AuditInspectorModal, AuditStatusBadge } from './AuditInspectorModal';

export const AdminAuditTab: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [filterUsername, setFilterUsername] = useState<string>('');
  const [filterDatabase, setFilterDatabase] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Selected Log for Inspector Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(async (targetPage: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params: AuditFilterParams = {
        page: targetPage,
        page_size: 20,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        username: filterUsername.trim() || undefined,
        target_database: filterDatabase.trim() || undefined,
        validation_status: filterStatus || undefined,
      };

      const res = await auditService.getAuditLogs(params);
      setLogs(res.items);
      setTotal(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch {
      setError('No se pudieron cargar los registros de auditoría.');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, filterUsername, filterDatabase, filterStatus]);

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs(1);
  };

  const handleClearFilters = () => {
    setStartDate('');
    setEndDate('');
    setFilterUsername('');
    setFilterDatabase('');
    setFilterStatus('');
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const params: AuditFilterParams = {
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        username: filterUsername.trim() || undefined,
        target_database: filterDatabase.trim() || undefined,
        validation_status: filterStatus || undefined,
      };
      await auditService.exportAuditLogsCsv(params);
    } catch {
      alert('Error al exportar archivo CSV de auditoría.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Registro de Auditoría & Trazabilidad de Consultas
          </h3>
          <p className="text-xs text-gray-400">
            Monitoreo en tiempo real de preguntas analíticas, SQL validado por AST Guardrail y estado de ejecución
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => fetchLogs(page)}
            disabled={loading}
            aria-label="Refrescar logs"
            className="p-2 rounded-xl bg-dark-card hover:bg-dark-border text-gray-300 hover:text-white transition-colors border border-dark-border"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exporting || logs.length === 0}
            className="flex items-center space-x-1.5 text-xs bg-dark-card hover:bg-dark-border text-emerald-400 font-semibold px-4 py-2 rounded-xl border border-emerald-500/30 transition-colors shadow-sm"
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
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Logs Table */}
      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-dark-base border-b border-dark-border text-gray-400 uppercase tracking-wider">
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
          <tbody className="divide-y divide-dark-border text-gray-200">
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-gray-400">
                  <div className="flex items-center justify-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                    <span>Cargando registros de auditoría...</span>
                  </div>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-gray-400">
                  No se encontraron consultas registradas con los filtros seleccionados.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-dark-card/50 transition-colors">
                  <td className="px-4 py-3 text-gray-400 font-mono text-[11px] whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{log.username}</div>
                    <div className="text-[10px] text-gray-400">{log.user_role || 'Sin Rol'}</div>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate text-gray-300" title={log.question_prompt}>
                    {log.question_prompt}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <AuditStatusBadge status={log.validation_status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 flex items-center space-x-1.5 whitespace-nowrap">
                    <Database className="w-3.5 h-3.5 text-gray-500" />
                    <span>{log.target_database || 'SQLite Demo'}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 font-mono whitespace-nowrap">
                    {log.execution_time_ms} ms
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => setSelectedLog(log)}
                      aria-label={`Ver detalles del log ID ${log.id}`}
                      className="p-1.5 rounded-lg bg-dark-card hover:bg-emerald-500/20 text-gray-400 hover:text-emerald-300 border border-dark-border hover:border-emerald-500/30 transition-colors"
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
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-400 pt-2">
        <div>
          Mostrando {logs.length} de {total} eventos registrados (Página {page} de {totalPages})
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => fetchLogs(page - 1)}
            disabled={page <= 1 || loading}
            aria-label="Página anterior"
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-dark-card hover:bg-dark-border disabled:opacity-40 disabled:pointer-events-none text-gray-300 transition-colors border border-dark-border"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Anterior</span>
          </button>
          <button
            type="button"
            onClick={() => fetchLogs(page + 1)}
            disabled={page >= totalPages || loading}
            aria-label="Página siguiente"
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-dark-card hover:bg-dark-border disabled:opacity-40 disabled:pointer-events-none text-gray-300 transition-colors border border-dark-border"
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
