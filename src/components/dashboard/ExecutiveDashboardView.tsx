import React, { useState, useMemo, useEffect } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
import { ExecutiveStudioView, ChartType } from './ExecutiveStudioView';
import { ExecutiveAssistantView } from './ExecutiveAssistantView';
import { THEME_COLORS, deriveProcessedRows, formatMetricNumber, buildDynamicChartOption } from './executiveDashboardUtils';
import { BarChart3, FileText, Table as TableIcon, ShieldCheck, Sparkles, Lightbulb, AlertTriangle, ShieldAlert, Database } from 'lucide-react';

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

const ExecutiveOfflineAlertView: React.FC<{
  result: QueryResult;
  onOpenTraceability?: () => void;
}> = ({ result, onOpenTraceability }) => {
  const vStatus = result.traceability?.validation_status || '';
  const isSecurityRejection = vStatus.includes('RECHAZADO') || vStatus.includes('BLOQUEADO') || vStatus.includes('AUTH');
  const isTrueOffline = result.summary_text?.includes('IA local no disponible') || vStatus.includes('DESCONECTADO');

  const alertTitle = isSecurityRejection
    ? 'Consulta Bloqueada por Gobernanza AST / RBAC'
    : isTrueOffline
    ? 'Motor LLM Local No Disponible'
    : 'Sin Registros Encontrados';

  const alertBadgeColor = isSecurityRejection
    ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
    : isTrueOffline
    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    : 'bg-blue-500/10 text-blue-400 border-blue-500/20';

  const borderTheme = isSecurityRejection
    ? 'border-rose-500/30'
    : isTrueOffline
    ? 'border-amber-500/30'
    : 'border-blue-500/30';

  const iconBg = isSecurityRejection
    ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 shadow-rose-500/10'
    : isTrueOffline
    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 shadow-amber-500/10'
    : 'bg-blue-500/10 border-blue-500/30 text-blue-400 shadow-blue-500/10';

  return (
    <div className={`w-full bg-gradient-to-br from-zinc-900/95 via-zinc-900/70 to-zinc-950/95 border ${borderTheme} rounded-3xl p-7 shadow-2xl space-y-6 animate-fadeIn`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div className="flex items-start sm:items-center space-x-3.5">
          <div className={`w-12 h-12 rounded-2xl border flex items-center justify-center shadow-lg shrink-0 ${iconBg}`}>
            {isSecurityRejection ? (
              <ShieldAlert className="w-6 h-6 text-rose-400" />
            ) : isTrueOffline ? (
              <AlertTriangle className="w-6 h-6 text-amber-400" />
            ) : (
              <Database className="w-6 h-6 text-blue-400" />
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <h3 className="text-base font-bold text-white tracking-tight">{alertTitle}</h3>
              <span className={`text-[10px] uppercase font-extrabold tracking-wider px-2.5 py-0.5 rounded-full border ${alertBadgeColor}`}>
                {vStatus || (isTrueOffline ? 'DESCONECTADO' : 'SIN_DATOS')}
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              {result.traceability?.explanation || (
                isSecurityRejection
                  ? 'El sistema de validación AST determinó que esta consulta infringe las directivas de seguridad o permisos de tu rol.'
                  : isTrueOffline
                  ? 'Se requiere un servidor de Inferencia IA activo para interpretar lenguaje natural.'
                  : 'La consulta SQL fue ejecutada sobre la base de datos pero no arrojó registros coincidentes.'
              )}
            </p>
          </div>
        </div>

        {onOpenTraceability && (
          <button
            onClick={onOpenTraceability}
            className={`flex items-center space-x-1.5 text-xs px-3.5 py-2 rounded-xl transition-colors shadow-sm font-semibold shrink-0 border ${
              isSecurityRejection
                ? 'text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border-rose-500/30'
                : 'text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/30'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Auditar SQL & AST</span>
          </button>
        )}
      </div>

      <div className="bg-zinc-950/80 border border-white/10 rounded-2xl p-5 text-sm text-zinc-200 leading-relaxed font-medium space-y-3 shadow-inner">
        <p className={isSecurityRejection ? 'text-rose-300 font-semibold' : isTrueOffline ? 'text-amber-300 font-semibold' : 'text-blue-300 font-semibold'}>
          {result.summary_text}
        </p>
        {isTrueOffline && (
          <p className="text-xs text-zinc-400">
            Para ejecutar consultas sobre la base de datos corporativa y generar visualizaciones analíticas en vivo, asegúrate de tener activo tu motor LLM local (Ollama en <code className="text-amber-400 font-mono">http://localhost:11434</code> o llama.cpp en <code className="text-amber-400 font-mono">http://127.0.0.1:8080</code>).
          </p>
        )}
        {isSecurityRejection && (
          <p className="text-xs text-zinc-400">
            El motor de Gobernanza Datia aplica el principio de mínimo privilegio. Para consultar tablas restringidas, contacta a un Administrador del sistema para otorgar los permisos necesarios en el Panel RBAC.
          </p>
        )}
      </div>

      <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400 border-t border-white/5">
        <div className="flex items-center space-x-3 flex-wrap gap-y-1">
          <span>Consulta: <strong className="text-zinc-200 font-mono">"{result.question}"</strong></span>
          <span>•</span>
          <span>Latencia: <strong className="text-zinc-200">{(((result.traceability?.execution_time_ms ?? 0)) / 1000).toFixed(2)}s</strong></span>
        </div>
        <span className="text-[11px] text-zinc-500">100% Gobernanza & Auditoría RBAC</span>
      </div>
    </div>
  );
};

interface ExecutiveDashboardHeaderProps {
  result: QueryResult;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  hasConversationalResponse: boolean;
  dataRowsCount: number;
  onOpenTraceability?: () => void;
}

const ExecutiveDashboardHeader: React.FC<ExecutiveDashboardHeaderProps> = ({
  result,
  viewMode,
  setViewMode,
  hasConversationalResponse,
  dataRowsCount,
  onOpenTraceability,
}) => {
  const dynamicTitle =
    result.response_type === 'greeting'
      ? 'Asistente de Datos IA'
      : result.response_type === 'report'
      ? 'Informe Ejecutivo de Negocio'
      : result.response_type === 'advisory' || result.response_type === 'explanation'
      ? 'Asesoría Estratégica IA'
      : 'Análisis Inteligente de Datos';

  const dynamicSubtitle =
    result.grounding_info || `Consulta "${result.question}" analizada en la base de datos activa`;

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-3xl p-5 shadow-2xl backdrop-blur-xl">
      <div className="flex items-center space-x-3.5">
        <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-base font-bold text-white tracking-tight">{dynamicTitle}</h2>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Live Data</span>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">{dynamicSubtitle}</p>
        </div>
      </div>

      <div className="flex items-center space-x-1.5 bg-zinc-950/80 p-1.5 rounded-2xl border border-white/5 self-start md:self-auto flex-wrap gap-y-1">
        {hasConversationalResponse && (
          <button
            onClick={() => setViewMode('assistant')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
              viewMode === 'assistant'
                ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Respuesta IA</span>
          </button>
        )}

        {dataRowsCount > 0 && (
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
        )}

        {result.executive_report && (
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
        )}

        {dataRowsCount > 0 && (
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
        )}

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
};

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability
}) => {
  const isOfflineOrError = useMemo(() => {
    const summary = result.summary_text || '';
    const status = result.traceability?.validation_status || '';
    const hasNoRows = !result.data_rows || result.data_rows.length === 0;
    return (
      summary.includes('IA local no disponible') ||
      status.includes('RECHAZADO') ||
      status.includes('DESCONECTADO') ||
      (hasNoRows && !result.conversational_response && (result.chart_type === 'none' || !result.chart_option?.series?.length))
    );
  }, [result]);

  const isAdvisoryOrExplanation = useMemo(() => {
    return (
      result.response_type === 'advisory' ||
      result.response_type === 'explanation' ||
      result.response_type === 'greeting' ||
      (Boolean(result.conversational_response) && (result.chart_type === 'none' || !result.chart_option?.series?.length))
    );
  }, [result.response_type, result.conversational_response, result.chart_type, result.chart_option]);

  const initialMode = useMemo<ViewMode>(() => {
    if (result.conversational_response) return 'assistant';
    if (isAdvisoryOrExplanation) return 'assistant';
    const hint = result.presentation_hints?.preferred_view;
    if (hint === 'report') return 'report';
    if (hint === 'table') return 'table';
    if (hint === 'assistant') return 'assistant';
    if (result.response_type === 'report') return 'report';
    return 'studio';
  }, [result.conversational_response, isAdvisoryOrExplanation, result.response_type, result.presentation_hints]);

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

  if (isOfflineOrError) {
    return (
      <ExecutiveOfflineAlertView
        result={result}
        onOpenTraceability={onOpenTraceability}
      />
    );
  }

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
            result={result}
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
