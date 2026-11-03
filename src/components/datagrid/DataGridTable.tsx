import React, { useState, useMemo, useEffect } from 'react';
import {
  Search,
  ArrowUpDown,
  Download,
  ChevronLeft,
  ChevronRight,
  Table,
  FileSpreadsheet,
  RefreshCw,
  Copy,
  Check,
  Calendar,
  Hash,
  DollarSign,
  Type,
} from 'lucide-react';
import { reportService } from '../../features/dashboard/services/report_service';
import { copyToClipboard } from '../../shared/clipboard';

type ColumnType = 'currency' | 'number' | 'date' | 'string';

const getColumnType = (col: string, sampleRows: Record<string, any>[]): ColumnType => {
  const lower = col.toLowerCase();
  if (/fecha|date|created_at|updated_at|timestamp|dia|mes|periodo/.test(lower)) {
    return 'date';
  }
  if (/precio|monto|total|costo|ingreso|venta|revenue|price|amount|salario|sueldo|presupuesto/.test(lower)) {
    return 'currency';
  }
  // Check sample rows
  for (const r of sampleRows) {
    const val = r[col];
    if (val !== null && val !== undefined && val !== '') {
      if (typeof val === 'number') {
        return 'number';
      }
      if (!isNaN(Number(val)) && typeof val !== 'boolean') {
        return 'number';
      }
      break;
    }
  }
  return 'string';
};

const renderColumnIcon = (type: ColumnType) => {
  switch (type) {
    case 'currency':
      return <DollarSign className="w-3 h-3 text-emerald-500 shrink-0" />;
    case 'number':
      return <Hash className="w-3 h-3 text-blue-500 shrink-0" />;
    case 'date':
      return <Calendar className="w-3 h-3 text-amber-500 shrink-0" />;
    default:
      return <Type className="w-3 h-3 text-slate-400 dark:text-zinc-500 shrink-0" />;
  }
};

const formatCellValue = (val: any, type: ColumnType): React.ReactNode => {
  if (val === null || val === undefined || val === '') {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-zinc-500 border border-slate-200 dark:border-zinc-700/60 select-none">
        NULL
      </span>
    );
  }

  if (type === 'currency') {
    const num = Number(val);
    if (!isNaN(num)) {
      return (
        <span className="font-mono tabular-nums text-slate-900 dark:text-gray-100">
          ${' '}
          {num.toLocaleString('es-CL', {
            minimumFractionDigits: num % 1 !== 0 ? 2 : 0,
            maximumFractionDigits: 2,
          })}
        </span>
      );
    }
  }

  if (type === 'number') {
    const num = Number(val);
    if (!isNaN(num)) {
      return (
        <span className="font-mono tabular-nums text-slate-900 dark:text-gray-100">
          {num.toLocaleString('es-CL', {
            minimumFractionDigits: num % 1 !== 0 ? 2 : 0,
            maximumFractionDigits: 2,
          })}
        </span>
      );
    }
  }

  return <span>{String(val)}</span>;
};

interface DataGridTableProps {
  columns: string[];
  rows: Record<string, any>[];
  question?: string;
  auditLogId?: number;
}

export const DataGridTable: React.FC<DataGridTableProps> = ({ columns, rows, question, auditLogId }) => {
  const [searchTerm, setSearchTerm] = useState('');
  // El filtro escanea TODAS las filas con `String()` por celda. Con el tope de
  // 500 filas y 15 columnas son miles de conversiones por pulsacion. El input
  // sigue escribiendo al instante (el control no se traba) pero la busqueda
  // corre 250 ms despues de la ultima tecla. Mismo criterio que
  // useAdminAudit: la ultima tecla gana.
  const [needle, setNeedle] = useState('');
  useEffect(() => {
    const id = setTimeout(() => setNeedle(searchTerm.trim().toLowerCase()), 250);
    return () => clearTimeout(id);
  }, [searchTerm]);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [copiedTSV, setCopiedTSV] = useState(false);
  const [pageSize, setPageSize] = useState<number>(10);

  const columnTypes = useMemo(() => {
    const map: Record<string, ColumnType> = {};
    for (const col of columns) {
      map[col] = getColumnType(col, rows);
    }
    return map;
  }, [columns, rows]);

  // Filter rows. El needle es el debounced (ver arriba), no el del input.
  const filteredRows = useMemo(() => {
    if (!needle) return rows;
    return rows.filter((row) =>
      Object.values(row).some(
        (val) => val !== null && val !== undefined && String(val).toLowerCase().includes(needle)
      )
    );
  }, [rows, needle]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;
    const sorted = [...filteredRows].sort((a, b) => {
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
    return sorted;
  }, [filteredRows, sortColumn, sortDirection]);

  // Pagination calculation. "Todas" used to mount every row: a 20k-row result
  // froze the tab for seconds. Capped, with the cap stated in the UI.
  const ALL_ROWS_CAP = 500;
  const effectivePageSize =
    pageSize === -1 ? Math.min(Math.max(sortedRows.length, 1), ALL_ROWS_CAP) : pageSize;
  const totalPages = Math.ceil(sortedRows.length / effectivePageSize) || 1;
  const paginatedRows = sortedRows.slice((currentPage - 1) * effectivePageSize, currentPage * effectivePageSize);


  const handleSort = (col: string) => {
    if (sortColumn === col) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(col);
      setSortDirection('asc');
    }
  };

  const handleCopyTSV = () => {
    if (!rows.length) return;
    const header = columns.join('\t');
    const body = sortedRows
      .map((row) => columns.map((col) => row[col] ?? '').join('\t'))
      .join('\n');
    void copyToClipboard(`${header}\n${body}`).then((ok: boolean) => {
      if (!ok) return;
      setCopiedTSV(true);
      setTimeout(() => setCopiedTSV(false), 2000);
    });
  };

  const handleExportCSV = () => {
    if (!rows.length) return;

    // RFC 4180: a cell containing a quote must double it, and an embedded newline
    // breaks the row count in Excel. Neither was escaped, so any text field
    // with a quotation mark or a multi-line note produced a CSV Excel refused
    // to open or silently mis-aligned.
    const csvCell = (v: unknown) =>
      '"' + String(v ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ') + '"';

    const header = columns.map(csvCell).join(',');
    const body = sortedRows
      .map((row) => columns.map((col) => csvCell(row[col])).join(','))
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
    <div className="glass-card rounded-2xl p-5 border border-slate-200 dark:border-white/10 space-y-4 bg-white dark:bg-zinc-900/90 shadow-xs">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Table className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate">Tabla de Datos Subyacente</h3>
          <span className="text-[11px] text-slate-600 dark:text-gray-400 bg-slate-100 dark:bg-dark-base px-2 py-0.5 rounded border border-slate-200 dark:border-dark-border shrink-0">
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
              className="w-full sm:w-44 bg-slate-50 dark:bg-dark-base border border-slate-300 dark:border-dark-border text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-gray-500 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-brand-500 transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-gray-500 absolute left-2.5 top-2" />
          </div>

          {/* Copy TSV Button (Compatible with Excel/Sheets Ctrl+V) */}
          <button
            type="button"
            onClick={handleCopyTSV}
            disabled={rows.length === 0}
            aria-label="Copiar datos para pegar en Excel o Sheets"
            className="flex items-center space-x-1 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-border text-slate-700 dark:text-gray-300 border border-slate-300 dark:border-dark-border px-2.5 py-1.5 rounded-lg transition-colors font-medium disabled:opacity-50 cursor-pointer"
            title="Copiar datos al portapapeles (compatible con Ctrl+V en Excel y Sheets)"
          >
            {copiedTSV ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">¡Copiado!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                <span>Copiar</span>
              </>
            )}
          </button>

          {/* Export CSV Button */}
          <button
            type="button"
            onClick={handleExportCSV}
            aria-label="Exportar datos a CSV"
            className="flex items-center space-x-1 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-border text-slate-700 dark:text-gray-300 border border-slate-300 dark:border-dark-border px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
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
            className="flex items-center space-x-1 text-xs bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-600/20 dark:hover:bg-emerald-600/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30 px-2.5 py-1.5 rounded-lg transition-colors font-medium disabled:opacity-50 cursor-pointer"
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
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-dark-border">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 dark:bg-dark-base/80 border-b border-slate-200 dark:border-dark-border text-xs text-slate-600 dark:text-gray-400 uppercase tracking-wider">
              {columns.map((col) => {
                const colType = columnTypes[col] || 'string';
                const isNumeric = colType === 'number' || colType === 'currency';
                const isDate = colType === 'date';

                return (
                  <th
                    key={col}
                    className={`px-4 py-3 font-semibold select-none ${
                      isNumeric ? 'text-right' : isDate ? 'text-center' : 'text-left'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSort(col)}
                      className={`inline-flex items-center space-x-1.5 text-slate-600 hover:text-slate-900 dark:text-gray-400 dark:hover:text-white transition-colors cursor-pointer focus:outline-none ${
                        isNumeric ? 'ml-auto' : isDate ? 'mx-auto' : ''
                      }`}
                      aria-label={`Ordenar por ${col}`}
                    >
                      {renderColumnIcon(colType)}
                      <span>{col}</span>
                      <ArrowUpDown
                        className={`w-3 h-3 ${
                          sortColumn === col
                            ? 'text-brand-600 dark:text-brand-400'
                            : 'text-slate-400 dark:text-gray-500'
                        }`}
                      />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-dark-border text-xs text-slate-800 dark:text-gray-200 bg-white dark:bg-transparent">
            {paginatedRows.length > 0 ? (
              paginatedRows.map((row, rowIndex) => {
                // El fallback anterior armaba la clave con las 15 columnas de
                // la fila, y eso corria en CADA render para cada fila. El
                // indice de la pagina cumple el mismo trabajo (la identidad la
                // da la posicion dentro de la pagina, y React solo necesita que
                // sea estable entre renders de la misma fila).
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
                  `row-${rowIndex}`;
                return (
                  <tr key={rowKey} className="hover:bg-slate-50 dark:hover:bg-dark-card/50 transition-colors">
                    {columns.map((col) => {
                      const val = row[col];
                      const colType = columnTypes[col] || 'string';
                      const isNumeric = colType === 'number' || colType === 'currency';
                      const isDate = colType === 'date';

                      return (
                        <td
                          key={col}
                          className={`px-4 py-2.5 whitespace-nowrap ${
                            isNumeric
                              ? 'text-right'
                              : isDate
                              ? 'text-center font-mono text-[11px]'
                              : 'text-left'
                          }`}
                        >
                          {formatCellValue(val, colType)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={columns.length} className="text-center py-6 text-slate-500 dark:text-gray-500 text-xs">
                  No se encontraron registros coincidentes.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-600 dark:text-gray-400 pt-1">
        <div className="flex items-center space-x-3 flex-wrap gap-y-1">
          <span>
            {sortedRows.length > 0 ? (
              <>
                Mostrando{' '}
                <strong className="text-slate-900 dark:text-gray-200">
                  {(currentPage - 1) * effectivePageSize + 1}-
                  {Math.min(currentPage * effectivePageSize, sortedRows.length)}
                </strong>{' '}
                de <strong className="text-slate-900 dark:text-gray-200">{sortedRows.length}</strong> registros
              </>
            ) : (
              '0 registros'
            )}
          </span>

          {/* Page Size Selector */}
          <div className="flex items-center space-x-1 pl-2 border-l border-slate-200 dark:border-dark-border">
            <span className="text-[11px] text-slate-500 dark:text-gray-500 font-medium">Filas:</span>
            {[5, 10, 25, 50, -1].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => {
                  setPageSize(size);
                  setCurrentPage(1);
                }}
                className={`px-2 py-0.5 rounded-md text-[11px] font-medium transition-colors ${
                  pageSize === size
                    ? 'bg-brand-50 text-brand-700 border border-brand-200 dark:bg-brand-600/30 dark:text-brand-300 dark:border-brand-500/40 font-semibold'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 border border-slate-200 dark:bg-dark-base dark:text-gray-400 dark:hover:text-white dark:border-dark-border'
                }`}
              >
                {size === -1
                  ? sortedRows.length > ALL_ROWS_CAP
                    ? `Primeras ${ALL_ROWS_CAP}`
                    : 'Todas'
                  : size}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto">
          <span className="text-[11px] text-slate-500 dark:text-gray-500">
            Página {currentPage} de {totalPages}
          </span>

          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            aria-label="Página anterior"
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 dark:bg-dark-base dark:border-dark-border text-slate-600 hover:text-slate-900 dark:text-gray-400 dark:hover:text-white disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            aria-label="Página siguiente"
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 dark:bg-dark-base dark:border-dark-border text-slate-600 hover:text-slate-900 dark:text-gray-400 dark:hover:text-white disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
};
