import React, { useState, useMemo, useEffect } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
import { ExecutiveStudioView, ChartType } from './ExecutiveStudioView';
import { ExecutiveAssistantView } from './ExecutiveAssistantView';
import { THEME_COLORS, deriveProcessedRows, formatMetricNumber, buildDynamicChartOption } from './executiveDashboardUtils';
import { BarChart3, FileText, Table as TableIcon, ShieldCheck, Sparkles, Lightbulb } from 'lucide-react';

interface ExecutiveDashboardViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
}

type ViewMode = 'assistant' | 'studio' | 'report' | 'table';
type ColorTheme = 'amber' | 'cyan' | 'emerald' | 'indigo';

interface ExecutiveDashboardHeaderProps {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  hasConversationalResponse: boolean;
  dataRowsCount: number;
  onOpenTraceability?: () => void;
}

const ExecutiveDashboardHeader: React.FC<ExecutiveDashboardHeaderProps> = ({
  viewMode,
  setViewMode,
  hasConversationalResponse,
  dataRowsCount,
  onOpenTraceability,
}) => (
  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-3xl p-5 shadow-2xl backdrop-blur-xl">
    <div className="flex items-center space-x-3.5">
      <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
        <Sparkles className="w-5 h-5" />
      </div>
      <div>
        <div className="flex items-center space-x-2">
          <h2 className="text-base font-bold text-white tracking-tight">Executive Analytics Studio</h2>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Live Data</span>
        </div>
        <p className="text-xs text-zinc-400 mt-0.5">Visualización analítica interactiva y reporte de gobernanza corporativa</p>
      </div>
    </div>

    <div className="flex items-center space-x-1.5 bg-zinc-950/80 p-1.5 rounded-2xl border border-white/5 self-start md:self-auto flex-wrap gap-y-1">
      {hasConversationalResponse && (
        <button
          onClick={() => setViewMode('assistant')}
          className="flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
        >
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Asistente</span>
        </button>
      )}

      <button
        onClick={() => setViewMode('studio')}
        className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
          viewMode === 'studio'
            ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
        }`}
      >
        <BarChart3 className="w-3.5 h-3.5" />
        <span>Studio</span>
      </button>

      <button
        onClick={() => setViewMode('report')}
        className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
          viewMode === 'report'
            ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
        }`}
      >
        <FileText className="w-3.5 h-3.5" />
        <span>Informe</span>
      </button>

      <button
        onClick={() => setViewMode('table')}
        className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
          viewMode === 'table'
            ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
        }`}
      >
        <TableIcon className="w-3.5 h-3.5" />
        <span>Dataset ({dataRowsCount})</span>
      </button>

      {onOpenTraceability && (
        <button
          onClick={onOpenTraceability}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border-l border-white/5 ml-1 transition-colors"
          title="Auditoría de Consulta SQL y Seguridad AST"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden sm:inline">SQL</span>
        </button>
      )}
    </div>
  </div>
);

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability
}) => {
  const isAdvisoryOrExplanation = useMemo(() => {
    return (
      result.response_type === 'advisory' ||
      result.response_type === 'explanation' ||
      (Boolean(result.conversational_response) && (result.chart_type === 'none' || !result.chart_option?.series?.length))
    );
  }, [result.response_type, result.conversational_response, result.chart_type, result.chart_option]);

  const initialMode = useMemo<ViewMode>(() => {
    if (isAdvisoryOrExplanation) return 'assistant';
    if (result.response_type === 'report') return 'report';
    return 'studio';
  }, [isAdvisoryOrExplanation, result.response_type]);

  const [viewMode, setViewMode] = useState<ViewMode>(initialMode);

  useEffect(() => {
    setViewMode(initialMode);
  }, [initialMode]);

  const [activeChartType, setActiveChartType] = useState<ChartType>(
    (result.chart_type as ChartType) || 'bar'
  );
  const [colorTheme, setColorTheme] = useState<ColorTheme>('amber');
  const [sortOrder, setSortOrder] = useState<'default' | 'desc' | 'asc'>('default');
  const [copiedReport, setCopiedReport] = useState(false);

  const currentTheme = THEME_COLORS[colorTheme];

  const { catCol, numCol, processedRows } = useMemo(
    () => deriveProcessedRows(result, sortOrder),
    [result, sortOrder]
  );

  const totalVal = useMemo(() => {
    if (!processedRows.length || !numCol) return 0;
    return processedRows.reduce((acc, r) => acc + (Number(r[numCol]) || 0), 0);
  }, [processedRows, numCol]);

  const maxValRow = useMemo(() => {
    if (!processedRows.length || !numCol) return null;
    return processedRows.reduce((max, r) => ((Number(r[numCol]) || 0) > (Number(max[numCol]) || 0) ? r : max), processedRows[0]);
  }, [processedRows, numCol]);

  const isCurrency = useMemo(() => {
    const colLower = (numCol || '').toLowerCase();
    const qLower = (result.question || '').toLowerCase();
    return (
      colLower.includes('monto') ||
      colLower.includes('ingreso') ||
      colLower.includes('precio') ||
      colLower.includes('salario') ||
      colLower.includes('costo') ||
      colLower.includes('usd') ||
      qLower.includes('ingreso') ||
      qLower.includes('precio') ||
      qLower.includes('salario') ||
      qLower.includes('monto')
    );
  }, [numCol, result.question]);

  const formatNumber = (num: number) => formatMetricNumber(num, isCurrency);

  const dynamicChartOption = useMemo(() => {
    return buildDynamicChartOption({
      processedRows,
      catCol,
      numCol,
      activeChartType,
      currentTheme,
      isCurrency,
      totalVal,
      fallbackChartOption: result.chart_option,
    });
  }, [processedRows, catCol, numCol, activeChartType, currentTheme, isCurrency, totalVal, result.chart_option]);

  const handleCopyReport = () => {
    const reportText = `INFORME EJECUTIVO DE NEGOCIO\nConsulta: "${result.question}"\nFecha: ${result.timestamp}\n\n1. RESUMEN EJECUTIVO:\n${result.executive_report?.overview || result.summary_text}\n\n2. HALLAZGOS CLAVE:\n${result.executive_report?.key_findings.map((f) => `  - ${f}`).join('\n') || '  - Registros procesados exitosamente.'}\n\n3. RECOMENDACIONES ESTRATÉGICAS:\n${result.executive_report?.recommendations.map((r) => `  - ${r}`).join('\n') || '  - Mantener monitoreo periódico.'}\n\n4. AUDITORÍA:\n  - SQL: ${result.traceability.sql_executed}\n  - Filas: ${result.traceability.rows_returned}\n  - Latencia: ${result.traceability.execution_time_ms} ms\n`;
    navigator.clipboard.writeText(reportText);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  return (
    <div className="w-full space-y-6">
      {viewMode === 'assistant' ? (
        <ExecutiveAssistantView
          result={result}
          onOpenTraceability={onOpenTraceability}
          onSwitchToStudio={() => setViewMode('studio')}
          onSwitchToReport={() => setViewMode('report')}
        />
      ) : (
        <>
          <ExecutiveDashboardHeader
            viewMode={viewMode}
            setViewMode={setViewMode}
            hasConversationalResponse={Boolean(result.conversational_response)}
            dataRowsCount={result.data_rows?.length || 0}
            onOpenTraceability={onOpenTraceability}
          />

          {viewMode === 'studio' && (
            <ExecutiveStudioView
              result={result}
              totalVal={totalVal}
              maxValRow={maxValRow}
              numCol={numCol}
              catCol={catCol}
              currentTheme={currentTheme}
              activeChartType={activeChartType}
              setActiveChartType={setActiveChartType}
              sortOrder={sortOrder}
              setSortOrder={setSortOrder}
              colorTheme={colorTheme}
              setColorTheme={setColorTheme}
              dynamicChartOption={dynamicChartOption}
              formatNumber={formatNumber}
              setViewMode={setViewMode}
            />
          )}

          {viewMode === 'report' && (
            <ExecutiveReportView
              result={result}
              formatNumber={formatNumber}
              totalVal={totalVal}
              maxValRow={maxValRow}
              catCol={catCol}
              copiedReport={copiedReport}
              onCopyReport={handleCopyReport}
              onOpenTraceability={onOpenTraceability}
            />
          )}

          {viewMode === 'table' && (
            <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <TableIcon className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-white tracking-tight">
                    Registros Extraídos de SQLite ({result.data_rows?.length || 0})
                  </h3>
                </div>
                <span className="text-xs text-zinc-400 bg-zinc-950 px-3 py-1 rounded-lg border border-white/5">
                  100% Sanitizado & Auditado
                </span>
              </div>
              <DataGridTable columns={result.data_columns} rows={result.data_rows} />
            </div>
          )}
        </>
      )}
    </div>
  );
};
