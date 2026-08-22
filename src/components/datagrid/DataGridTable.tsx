import React, { useState } from 'react';
import { Search, ArrowUpDown, Download, ChevronLeft, ChevronRight, Table, FileSpreadsheet, RefreshCw } from 'lucide-react';
import { reportService } from '../../services/report_service';

interface DataGridTableProps {
  columns: string[];
  rows: Record<string, any>[];
  question?: string;
  auditLogId?: number;
}

export const DataGridTable: React.FC<DataGridTableProps> = ({ columns, rows, question, auditLogId }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const pageSize = 5;

  // Filter rows
  const filteredRows = rows.filter((row) =>
    Object.values(row).some(
      (val) => val !== null && val !== undefined && String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  // Sort rows
  const sortedRows = [...filteredRows].sort((a, b) => {
    if (!sortColumn) return 0;
    const valA = a[sortColumn];
    const valB = b[sortColumn];

    if (valA === valB) return 0;
    if (valA === null || valA === undefined) return 1;
    if (valB === null || valB === undefined) return -1;

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortDirection === 'asc' ? valA - valB : valB - valA;
    }
    return sortDirection === 'asc'
      ? String(valA).localeCompare(String(valB))
      : String(valB).localeCompare(String(valA));
  });

  // Pagination
  const totalPages = Math.ceil(sortedRows.length / pageSize) || 1;
  const paginatedRows = sortedRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleSort = (col: string) => {
    if (sortColumn === col) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(col);
      setSortDirection('asc');
    }
  };

  const handleExportCSV = () => {
    if (!rows.length) return;
    const header = columns.join(',');
    const body = sortedRows
      .map((row) => columns.map((col) => `"${row[col] ?? ''}"`).join(','))
      .join('\n');
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `exportacion_datos_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleExportExcel = async () => {
    if (!rows.length) return;
    if (auditLogId) {
      setIsExportingExcel(true);
      try {
        await reportService.exportExecutiveReportExcel({ audit_log_id: auditLogId });
      } catch {
        handleExportCSV();
      } finally {
        setIsExportingExcel(false);
      }
    } else {
      handleExportCSV();
    }
  };

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/10 space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Table className="w-4 h-4 text-brand-400 shrink-0" />
          <h3 className="text-sm font-semibold text-white truncate">Tabla de Datos Subyacente</h3>
          <span className="text-[11px] text-gray-400 bg-dark-base px-2 py-0.5 rounded border border-dark-border shrink-0">
            {filteredRows.length} registros
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search Box */}
          <div className="relative flex-1 sm:flex-none">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Buscar en la tabla..."
              aria-label="Buscar en la tabla"
              className="w-full sm:w-44 bg-dark-base border border-dark-border text-xs text-white placeholder-gray-500 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-brand-500 transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-gray-500 absolute left-2.5 top-2" />
          </div>

          {/* Export CSV Button */}
          <button
            type="button"
            onClick={handleExportCSV}
            aria-label="Exportar datos a CSV"
            className="flex items-center space-x-1 text-xs bg-dark-base hover:bg-dark-border text-gray-300 border border-dark-border px-2.5 py-1.5 rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>

          {/* Export Excel Button */}
          <button
            type="button"
            onClick={handleExportExcel}
            disabled={isExportingExcel || rows.length === 0}
            aria-label="Exportar datos a Excel"
            className="flex items-center space-x-1 text-xs bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 px-2.5 py-1.5 rounded-lg transition-colors font-medium disabled:opacity-50"
          >
            {isExportingExcel ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-3.5 h-3.5" />
            )}
            <span>Excel</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-dark-base/80 border-b border-dark-border text-xs text-gray-400 uppercase tracking-wider">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 font-semibold select-none"
                >
                  <button
                    type="button"
                    onClick={() => handleSort(col)}
                    className="flex items-center space-x-1 text-gray-400 hover:text-white transition-colors cursor-pointer text-left focus:outline-none focus:text-white"
                    aria-label={`Ordenar por ${col}`}
                  >
                    <span>{col}</span>
                    <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border text-xs text-gray-200">
            {paginatedRows.length > 0 ? (
              paginatedRows.map((row, idx) => {
                const rowKey =
                  row.id ??
                  row.id_venta ??
                  row.id_producto ??
                  row.id_cliente ??
                  row.id_empleado ??
                  row.id_servidor ??
                  row.id_registro ??
                  row.id_incidente ??
                  row.id_consumo ??
                  row.id_categoria ??
                  columns.map((c) => String(row[c])).join('-');
                return (
                  <tr key={rowKey} className="hover:bg-dark-card/50 transition-colors">
                    {columns.map((col) => (
                      <td key={col} className="px-4 py-2.5 whitespace-nowrap">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                      </td>
                    ))}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={columns.length} className="text-center py-6 text-gray-500 text-xs">
                  No se encontraron registros coincidentes.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between text-xs text-gray-400 pt-1">
        <div>
          Página {currentPage} de {totalPages}
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            aria-label="Página anterior"
            className="p-1.5 rounded-lg bg-dark-base border border-dark-border text-gray-400 hover:text-white disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            aria-label="Página siguiente"
            className="p-1.5 rounded-lg bg-dark-base border border-dark-border text-gray-400 hover:text-white disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
