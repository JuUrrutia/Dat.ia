import React, { useState } from 'react';
import { QueryResult } from '../../types';
import {
  FileText,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react';
import { formatMetricNumber } from '../dashboard/executiveDashboardUtils';
import { ReportExportToolbar } from './report/ReportExportToolbar';
import { ReportFindingsView } from './report/ReportFindingsView';

interface ExecutiveReportViewProps {
  result: QueryResult;
  formatNumber?: (num: number) => string;
  totalVal?: number;
  maxValRow?: Record<string, any> | null;
  catCol?: string;
  copiedReport?: boolean;
  onCopyReport?: () => void;
  onOpenTraceability?: () => void;
}

export const ExecutiveReportView: React.FC<ExecutiveReportViewProps> = ({
  result,
  formatNumber = (n) => formatMetricNumber(n, false),
  totalVal = 0,
  maxValRow = null,
  catCol = 'Categoría',
  copiedReport: externalCopied,
  onCopyReport: externalCopyHandler,
  onOpenTraceability,
}) => {
  const [exportError, setExportError] = useState<string | null>(null);
  const [internalCopied, setInternalCopied] = useState(false);

  const copiedReport = externalCopied ?? internalCopied;

  const onCopyReport = externalCopyHandler || (() => {
    const textToCopy = result.executive_report?.overview || result.summary_text || '';
    navigator.clipboard.writeText(textToCopy);
    setInternalCopied(true);
    setTimeout(() => setInternalCopied(false), 2000);
  });

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

        <ReportExportToolbar
          result={result}
          copiedReport={copiedReport}
          onCopyReport={onCopyReport}
          onExportError={setExportError}
        />
      </div>

      {exportError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{exportError}</span>
        </div>
      )}

      {/* Report Findings & Strategic Sections */}
      <ReportFindingsView
        result={result}
        formatNumber={formatNumber}
        totalVal={totalVal}
        maxValRow={maxValRow}
        catCol={catCol}
      />

      {/* Section 4: Technical Traceability & Governance */}
      <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400">
        <div className="flex items-center space-x-4">
          <span>SQL: <strong className="text-zinc-200">{result.traceability?.validation_status || 'APROBADO'}</strong></span>
          <span>Filas: <strong className="text-zinc-200">{result.traceability?.rows_returned || result.data_rows?.length || 0}</strong></span>
          <span>Latencia: <strong className="text-zinc-200">{result.traceability?.execution_time_ms || 0} ms</strong></span>
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
