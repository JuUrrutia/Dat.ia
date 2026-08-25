import React, { useState } from 'react';
import { QueryResult } from '../../../types';
import {
  FileText,
  Copy,
  Check,
  Download,
  FileSpreadsheet,
  RefreshCw,
  ChevronDown,
} from 'lucide-react';
import { reportService } from '../../../services/report_service';

interface ReportExportToolbarProps {
  result: QueryResult;
  copiedReport: boolean;
  onCopyReport: () => void;
  onExportError: (msg: string | null) => void;
}

export const ReportExportToolbar: React.FC<ReportExportToolbarProps> = ({
  result,
  copiedReport,
  onCopyReport,
  onExportError,
}) => {
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);

  const handleExportPdf = async () => {
    setIsExportingPdf(true);
    onExportError(null);
    setIsExportMenuOpen(false);
    try {
      const chartBase64 = await reportService.captureChartAsBase64();
      await reportService.exportExecutiveReportPdf(result, chartBase64);
    } catch (err: any) {
      onExportError(err.response?.data?.detail || 'Error al generar el informe en PDF.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleExportExcel = async () => {
    setIsExportingExcel(true);
    onExportError(null);
    setIsExportMenuOpen(false);
    try {
      await reportService.exportExecutiveReportExcel(result);
    } catch (err: any) {
      onExportError(err.response?.data?.detail || 'Error al generar el archivo Excel.');
    } finally {
      setIsExportingExcel(false);
    }
  };

  return (
    <div className="flex items-center space-x-3">
      {/* Copy Report Button */}
      <button
        type="button"
        onClick={onCopyReport}
        aria-label="Copiar informe ejecutivo"
        className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition-colors shadow-lg shadow-amber-500/10"
      >
        {copiedReport ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        <span>{copiedReport ? '¡Copiado!' : 'Copiar'}</span>
      </button>

      {/* Export Dropdown Menu */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsExportMenuOpen((prev) => !prev)}
          disabled={isExportingPdf || isExportingExcel}
          aria-label="Menú exportar informe"
          aria-expanded={isExportMenuOpen}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold transition-colors shadow-lg shadow-indigo-600/20 disabled:opacity-50"
        >
          {isExportingPdf || isExportingExcel ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          <span>Exportar</span>
          <ChevronDown className="w-3.5 h-3.5" />
        </button>

        {isExportMenuOpen && (
          <div className="absolute right-0 mt-2 w-48 rounded-xl bg-zinc-900 border border-white/10 shadow-2xl p-1.5 z-30 space-y-1 animate-fadeIn">
            <button
              type="button"
              onClick={handleExportPdf}
              disabled={isExportingPdf}
              className="w-full flex items-center space-x-2 px-3 py-2 text-xs text-zinc-200 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors text-left"
            >
              <FileText className="w-4 h-4 text-rose-400 shrink-0" />
              <span>Descargar PDF</span>
            </button>
            <button
              type="button"
              onClick={handleExportExcel}
              disabled={isExportingExcel}
              className="w-full flex items-center space-x-2 px-3 py-2 text-xs text-zinc-200 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors text-left"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Descargar Excel</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
