import React, { useState } from 'react';
import { QueryResult } from '../../types';
import {
  FileText,
  Copy,
  Check,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  Download,
  FileSpreadsheet,
  RefreshCw,
  ChevronDown,
} from 'lucide-react';
import { reportService } from '../../services/report_service';

interface ExecutiveReportViewProps {
  result: QueryResult;
  formatNumber: (num: number) => string;
  totalVal: number;
  maxValRow: Record<string, any> | null;
  catCol: string;
  copiedReport: boolean;
  onCopyReport: () => void;
  onOpenTraceability?: () => void;
}

export const ExecutiveReportView: React.FC<ExecutiveReportViewProps> = ({
  result,
  formatNumber,
  totalVal,
  maxValRow,
  catCol,
  copiedReport,
  onCopyReport,
  onOpenTraceability,
}) => {
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportPdf = async () => {
    setIsExportingPdf(true);
    setExportError(null);
    setIsExportMenuOpen(false);
    try {
      const chartBase64 = await reportService.captureChartAsBase64();
      await reportService.exportExecutiveReportPdf(result, chartBase64);
    } catch (err: any) {
      setExportError(err.response?.data?.detail || 'Error al generar el informe en PDF.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleExportExcel = async () => {
    setIsExportingExcel(true);
    setExportError(null);
    setIsExportMenuOpen(false);
    try {
      await reportService.exportExecutiveReportExcel(result);
    } catch (err: any) {
      setExportError(err.response?.data?.detail || 'Error al generar el archivo Excel.');
    } finally {
      setIsExportingExcel(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-zinc-900/95 via-zinc-900/60 to-zinc-950/95 border border-white/10 rounded-3xl p-7 shadow-2xl space-y-7 animate-fadeIn">
      {/* Report Title & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/10">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-amber-400" />
            <h3 className="text-lg font-bold text-white tracking-tight">
              Informe Ejecutivo de Negocio
            </h3>
          </div>
          <p className="text-xs text-zinc-400">
            Generado automáticamente a partir de la consulta "{result.question}" sobre la base de datos activa.
          </p>
        </div>

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
      </div>

      {exportError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{exportError}</span>
        </div>
      )}

      {/* Section 1: Overview & Risk Assessment */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>1. Diagnóstico & Contexto General</span>
          </h4>

          {result.executive_report?.risk_level && (
            <span
              className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full border ${
                result.executive_report.risk_level === 'ALTO' || result.executive_report.risk_level === 'CRITICO'
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : result.executive_report.risk_level === 'MEDIO'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              }`}
            >
              Nivel de Riesgo: {result.executive_report.risk_level}
            </span>
          )}
        </div>

        <div className="bg-zinc-950/70 border border-white/10 rounded-2xl p-5 text-sm text-zinc-200 leading-relaxed font-normal shadow-inner">
          {result.executive_report?.overview || result.summary_text}
        </div>

        {result.executive_report?.business_impact && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-200/90">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-amber-300 font-semibold">Impacto Directo en el Negocio: </strong>
              <span>{result.executive_report.business_impact}</span>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Key Findings */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>2. Hallazgos Clave & Puntos Críticos</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(result.executive_report?.key_findings && result.executive_report.key_findings.length > 0
            ? result.executive_report.key_findings
            : [
                `Se procesaron ${result.data_rows?.length || 0} registros de la base de datos activa.`,
                `El valor total acumulado analizado asciende a ${formatNumber(totalVal)}.`,
                `El registro con mayor ponderación corresponde a ${String(maxValRow?.[catCol] || 'Líder')}.`
              ]
          ).map((finding) => (
            <div
              key={finding}
              className="bg-zinc-950/70 border border-white/10 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-emerald-500/30 transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed font-normal">{finding}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Strategic Recommendations */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>3. Recomendaciones Estratégicas Accionables</span>
        </h4>
        <div className="space-y-2.5">
          {(result.executive_report?.recommendations && result.executive_report.recommendations.length > 0
            ? result.executive_report.recommendations
            : [
                'Mantener el monitoreo continuo de estos indicadores clave.',
                'Evaluar la asignación de recursos basada en las tendencias observadas.',
                'Compartir este informe con los líderes de área correspondientes.'
              ]
          ).map((rec, idx) => (
            <div
              key={rec}
              className="bg-zinc-950/70 border border-cyan-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-cyan-500/40 transition-colors"
            >
              <div className="w-5 h-5 rounded-lg bg-cyan-500/20 text-cyan-300 font-extrabold flex items-center justify-center text-[10px] shrink-0 mt-0.5 border border-cyan-500/30">
                {idx + 1}
              </div>
              <span className="leading-relaxed font-normal">{rec}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: Technical Traceability & Governance */}
      <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400">
        <div className="flex items-center space-x-4">
          <span>SQL: <strong className="text-zinc-200">{result.traceability.validation_status}</strong></span>
          <span>Filas: <strong className="text-zinc-200">{result.traceability.rows_returned}</strong></span>
          <span>Latencia: <strong className="text-zinc-200">{result.traceability.execution_time_ms} ms</strong></span>
        </div>

        {onOpenTraceability && (
          <button
            type="button"
            onClick={onOpenTraceability}
            className="flex items-center space-x-1.5 text-amber-400 hover:text-amber-300 font-medium"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Auditar Código SQL Completo</span>
          </button>
        )}
      </div>
    </div>
  );
};
