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
  Sliders,
  X,
} from 'lucide-react';
import { reportService } from '../../../features/dashboard/services/report_service';

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
  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false);

  // Customization fields
  const [customTitle, setCustomTitle] = useState(result.question || '');
  const [customNotes, setCustomNotes] = useState('');
  const [includeRawData, setIncludeRawData] = useState(true);

  const handleExportPdf = async (customized = false) => {
    setIsExportingPdf(true);
    onExportError(null);
    setIsExportMenuOpen(false);
    if (customized) setIsCustomizeOpen(false);
    try {
      const chartBase64 = await reportService.captureChartAsBase64();
      await reportService.exportExecutiveReportPdf(result, {
        chartBase64,
        custom_title: customized ? customTitle.trim() : undefined,
        custom_notes: customized ? customNotes.trim() : undefined,
        include_raw_data: customized ? includeRawData : true,
      });
    } catch (err: any) {
      onExportError(err.response?.data?.detail || 'Error al generar el informe en PDF.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleExportExcel = async (customized = false) => {
    setIsExportingExcel(true);
    onExportError(null);
    setIsExportMenuOpen(false);
    if (customized) setIsCustomizeOpen(false);
    try {
      await reportService.exportExecutiveReportExcel(result, {
        custom_title: customized ? customTitle.trim() : undefined,
        custom_notes: customized ? customNotes.trim() : undefined,
        include_raw_data: customized ? includeRawData : true,
      });
    } catch (err: any) {
      onExportError(err.response?.data?.detail || 'Error al generar el archivo Excel.');
    } finally {
      setIsExportingExcel(false);
    }
  };

  return (
    <>
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
            <div className="absolute right-0 mt-2 w-52 rounded-xl bg-zinc-900 border border-white/10 shadow-2xl p-1.5 z-30 space-y-1 animate-fadeIn">
              <button
                type="button"
                onClick={() => handleExportPdf(false)}
                disabled={isExportingPdf}
                className="w-full flex items-center space-x-2 px-3 py-2 text-xs text-zinc-200 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors text-left"
              >
                <FileText className="w-4 h-4 text-rose-400 shrink-0" />
                <span>Descargar PDF</span>
              </button>
              <button
                type="button"
                onClick={() => handleExportExcel(false)}
                disabled={isExportingExcel}
                className="w-full flex items-center space-x-2 px-3 py-2 text-xs text-zinc-200 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors text-left"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Descargar Excel</span>
              </button>
              <div className="border-t border-zinc-800 my-1"></div>
              <button
                type="button"
                onClick={() => {
                  setIsExportMenuOpen(false);
                  setIsCustomizeOpen(true);
                }}
                className="w-full flex items-center space-x-2 px-3 py-2 text-xs text-indigo-300 hover:text-white hover:bg-indigo-600/30 rounded-lg transition-colors text-left"
              >
                <Sliders className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Personalizar Reporte...</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Report Customizer Modal */}
      {isCustomizeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-lg rounded-2xl bg-zinc-900 border border-zinc-700/80 shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center space-x-2 text-white font-semibold text-sm">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <span>Personalizar Informe Ejecutivo</span>
              </div>
              <button
                type="button"
                onClick={() => setIsCustomizeOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">Título del Reporte</label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-hidden focus:border-indigo-500"
                  placeholder="Ej: Análisis Estratégico de Ventas Q3"
                />
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">Notas Ejecutivas / Observaciones</label>
                <textarea
                  rows={3}
                  value={customNotes}
                  onChange={(e) => setCustomNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-hidden focus:border-indigo-500 resize-none"
                  placeholder="Agregue contexto para la junta directiva o instrucciones accionables..."
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="includeRawDataCheckbox"
                  checked={includeRawData}
                  onChange={(e) => setIncludeRawData(e.target.checked)}
                  className="w-4 h-4 rounded-sm bg-zinc-950 border-zinc-700 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="includeRawDataCheckbox" className="text-zinc-300 select-none cursor-pointer">
                  Incluir tabla detallada de datos crudos (Hoja Excel / Anexo PDF)
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setIsCustomizeOpen(false)}
                className="px-3 py-1.5 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors text-xs font-medium"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => handleExportExcel(true)}
                disabled={isExportingExcel}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-medium transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Exportar Excel</span>
              </button>
              <button
                type="button"
                onClick={() => handleExportPdf(true)}
                disabled={isExportingPdf}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors shadow-lg shadow-indigo-600/20"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Exportar PDF</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
