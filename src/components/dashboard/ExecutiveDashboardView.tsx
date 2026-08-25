import React, { useState, useMemo, useEffect } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
import { ExecutiveStudioView } from './ExecutiveStudioView';
import { ExecutiveAssistantView } from './ExecutiveAssistantView';
import { KPISection } from '../../features/dashboard/components/KPISection';
import { ChartSection } from '../../features/dashboard/components/ChartSection';
import { OfflineAlertView } from '../../features/dashboard/components/OfflineAlertView';
import { ColorTheme } from './executiveDashboardUtils';
import { BarChart3, FileText, Table as TableIcon, Sparkles } from 'lucide-react';

interface ExecutiveDashboardViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
}

type ViewMode = 'assistant' | 'studio' | 'report' | 'table';

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
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-zinc-900/90 border border-white/10 p-3.5 rounded-2xl shadow-xl backdrop-blur-md">
      <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-none pb-1 sm:pb-0">
        {hasConversationalResponse && (
          <button
            onClick={() => setViewMode('assistant')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
              viewMode === 'assistant'
                ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/20'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Respuesta IA</span>
          </button>
        )}

        <button
          onClick={() => setViewMode('studio')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            viewMode === 'studio'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Studio Visual</span>
        </button>

        <button
          onClick={() => setViewMode('report')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            viewMode === 'report'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Informe Ejecutivo</span>
        </button>

        <button
          onClick={() => setViewMode('table')}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
            viewMode === 'table'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
          }`}
        >
          <TableIcon className="w-3.5 h-3.5" />
          <span>Datos ({dataRowsCount})</span>
        </button>
      </div>
    </div>
  );
};

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability,
}) => {
  const [colorTheme, setColorTheme] = useState<ColorTheme>('indigo');

  const hasConversationalResponse = Boolean(result.conversational_response);

  const initialMode = useMemo<ViewMode>(() => {
    if (result.presentation_hints?.preferred_view === 'assistant' && hasConversationalResponse) {
      return 'assistant';
    }
    if (result.presentation_hints?.preferred_view === 'table') {
      return 'table';
    }
    if (hasConversationalResponse) {
      return 'assistant';
    }
    return 'studio';
  }, [result, hasConversationalResponse]);

  const [viewMode, setViewMode] = useState<ViewMode>(initialMode);

  useEffect(() => {
    setViewMode(initialMode);
  }, [initialMode, result.id]);

  const vStatus = result.traceability?.validation_status || '';
  const isSecurityRejection = vStatus.includes('RECHAZADO') || vStatus.includes('BLOQUEADO') || vStatus.includes('AUTH');
  const isOfflineMode = result.summary_text?.includes('IA local no disponible') || vStatus.includes('DESCONECTADO');
  const hasNoRows = !result.data_rows || result.data_rows.length === 0;

  // Render Alert if error/offline/empty
  if (isSecurityRejection || isOfflineMode || (hasNoRows && !hasConversationalResponse)) {
    return (
      <OfflineAlertView
        result={result}
        onOpenTraceability={onOpenTraceability}
      />
    );
  }

  return (
    <div className="w-full space-y-6 animate-fadeIn">
      {/* Header Selector Tabs */}
      <ExecutiveDashboardHeader
        viewMode={viewMode}
        setViewMode={setViewMode}
        hasConversationalResponse={hasConversationalResponse}
        dataRowsCount={result.data_rows?.length || 0}
        onOpenTraceability={onOpenTraceability}
      />

      {/* Main View Switching */}
      {viewMode === 'assistant' && (
        <ExecutiveAssistantView
          result={result}
          onOpenTraceability={onOpenTraceability}
          onSwitchToStudio={() => setViewMode('studio')}
          onSwitchToReport={() => setViewMode('report')}
        />
      )}

      {viewMode === 'studio' && (
        <div className="space-y-6">
          <KPISection
            kpis={result.kpis}
            gauges={result.gauges}
            colorTheme={colorTheme}
          />
          <ChartSection
            result={result}
            colorTheme={colorTheme}
            onThemeChange={setColorTheme}
          />
          {result.data_rows && result.data_rows.length > 0 && (
            <DataGridTable
              columns={result.data_columns}
              rows={result.data_rows}
              question={result.question}
              auditLogId={result.traceability?.audit_log_id || result.audit_log_id}
            />
          )}
        </div>
      )}

      {viewMode === 'report' && (
        <ExecutiveReportView
          result={result}
          onOpenTraceability={onOpenTraceability}
        />
      )}

      {viewMode === 'table' && result.data_rows && (
        <DataGridTable
          columns={result.data_columns}
          rows={result.data_rows}
          question={result.question}
          auditLogId={result.traceability?.audit_log_id || result.audit_log_id}
        />
      )}
    </div>
  );
};
