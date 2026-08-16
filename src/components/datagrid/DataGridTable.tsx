import React, { useState } from 'react';
import { Search, ArrowUpDown, Download, ChevronLeft, ChevronRight, Table } from 'lucide-react';

interface DataGridTableProps {
  columns: string[];
  rows: Record<string, any>[];
}

export const DataGridTable: React.FC<DataGridTableProps> = ({ columns, rows }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
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
  };

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/10 space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Table className="w-4 h-4 text-brand-400" />
          <h3 className="text-sm font-semibold text-white">Tabla de Datos Subyacente</h3>
          <span className="text-xs text-gray-400 bg-dark-base px-2 py-0.5 rounded border border-dark-border">
            {filteredRows.length} registros
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {/* Search Box */}
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Buscar en la tabla..."
              className="bg-dark-base border border-dark-border text-xs text-white placeholder-gray-500 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-brand-500 transition-all w-48"
            />
            <Search className="w-3.5 h-3.5 text-gray-500 absolute left-2.5 top-2" />
          </div>

          {/* Export CSV Button */}
          <button
            onClick={handleExportCSV}
            className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-gray-300 border border-dark-border px-3 py-1.5 rounded-lg transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
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
                  onClick={() => handleSort(col)}
                  className="px-4 py-3 cursor-pointer hover:text-white transition-all font-semibold select-none"
                >
                  <div className="flex items-center space-x-1">
                    <span>{col}</span>
                    <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border text-xs text-gray-200">
            {paginatedRows.length > 0 ? (
              paginatedRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-dark-card/50 transition-all">
                  {columns.map((col) => (
                    <td key={col} className="px-4 py-2.5 whitespace-nowrap">
                      {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                    </td>
                  ))}
                </tr>
              ))
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
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded-lg bg-dark-base border border-dark-border text-gray-400 hover:text-white disabled:opacity-40 transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded-lg bg-dark-base border border-dark-border text-gray-400 hover:text-white disabled:opacity-40 transition-all"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
