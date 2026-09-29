import React from 'react';
import { Search, Filter } from 'lucide-react';

interface AuditFiltersProps {
  startDate: string;
  endDate: string;
  filterUsername: string;
  filterDatabase: string;
  filterStatus: string;
  loading: boolean;
  onStartDateChange: (val: string) => void;
  onEndDateChange: (val: string) => void;
  onUsernameChange: (val: string) => void;
  onDatabaseChange: (val: string) => void;
  onStatusChange: (val: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onClear: () => void;
}

export const AuditFilters: React.FC<AuditFiltersProps> = ({
  startDate,
  endDate,
  filterUsername,
  filterStatus,
  loading,
  onStartDateChange,
  onEndDateChange,
  onUsernameChange,
  onStatusChange,
  onSubmit,
  onClear,
}) => {
  return (
    <form
      onSubmit={onSubmit}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs bg-slate-50 dark:bg-dark-base/40 p-4 rounded-xl border border-slate-200 dark:border-dark-border"
    >
      <div>
        <label htmlFor="audit-filter-user" className="block text-gray-700 dark:text-gray-400 font-medium mb-1">
          Usuario
        </label>
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            id="audit-filter-user"
            aria-label="Filtrar por usuario"
            type="text"
            value={filterUsername}
            onChange={(e) => onUsernameChange(e.target.value)}
            placeholder="Buscar usuario..."
            className="w-full bg-white dark:bg-dark-base border border-slate-300 dark:border-dark-border rounded-xl pl-9 pr-3 py-1.5 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      <div>
        <label htmlFor="audit-filter-status" className="block text-gray-700 dark:text-gray-400 font-medium mb-1">
          Estado Validación
        </label>
        <select
          id="audit-filter-status"
          aria-label="Filtrar por estado de validación"
          value={filterStatus}
          onChange={(e) => onStatusChange(e.target.value)}
          className="w-full bg-white dark:bg-dark-base border border-slate-300 dark:border-dark-border rounded-xl px-3 py-1.5 text-gray-900 dark:text-white focus:outline-none focus:border-emerald-500"
        >
          <option value="">Todos los Estados</option>
          <option value="APROBADO">Aprobado (SELECT)</option>
          <option value="RECHAZADO">Rechazado por RBAC / Guardrail</option>
          <option value="ERROR">Error Sintáctico / Ejecución</option>
        </select>
      </div>

      <div>
        <label htmlFor="audit-filter-start" className="block text-gray-700 dark:text-gray-400 font-medium mb-1">
          Fecha Desde
        </label>
        <input
          id="audit-filter-start"
          aria-label="Fecha inicio filtro"
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="w-full bg-white dark:bg-dark-base border border-slate-300 dark:border-dark-border rounded-xl px-3 py-1.5 text-gray-900 dark:text-white focus:outline-none focus:border-emerald-500"
        />
      </div>

      <div>
        <label htmlFor="audit-filter-end" className="block text-gray-700 dark:text-gray-400 font-medium mb-1">
          Fecha Hasta
        </label>
        <input
          id="audit-filter-end"
          aria-label="Fecha fin filtro"
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="w-full bg-white dark:bg-dark-base border border-slate-300 dark:border-dark-border rounded-xl px-3 py-1.5 text-gray-900 dark:text-white focus:outline-none focus:border-emerald-500"
        />
      </div>

      <div className="flex items-end space-x-2">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 flex items-center justify-center space-x-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-1.5 px-3 rounded-xl transition-colors shadow-xs cursor-pointer"
        >
          <Filter className="w-3.5 h-3.5" />
          <span>Filtrar</span>
        </button>
        <button
          type="button"
          onClick={onClear}
          className="px-3 py-1.5 rounded-xl bg-slate-200 dark:bg-dark-card hover:bg-slate-300 dark:hover:bg-dark-border text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
        >
          Limpiar
        </button>
      </div>
    </form>
  );
};
