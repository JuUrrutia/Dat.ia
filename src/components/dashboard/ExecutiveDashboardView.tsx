import React, { useState, useMemo, useEffect } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
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

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability,
}) => {
  const [colorTheme, setColorTheme] = useState<ColorTheme>('indigo');

  const hasConversationalResponse = Boolean(result.conversational_response || result.summary_text);
  const hasDataRows = Boolean(result.data_rows && result.data_rows.length > 0);
  const hasChart = Boolean(result.chart_type && result.chart_type !== 'none' && result.chart_option);

  const initialMode = useMemo<ViewMode>(() => {
    if (result.presentation_hints?.preferred_view === 'table') {
      return 'table';
    }
    return 'assistant';
  }, [result]);

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
    <div className="w-full space-y-4 animate-fadeIn font-sans">
      {/* Optional Mode Switcher Tabs (Only if there are multiple data views available and user switched view) */}
      {(hasChart || hasDataRows || result.executive_report) && (
        <div className="flex items-center space-x-1.5 bg-dark-base/80 p-1 rounded-xl border border-dark-border/80 w-fit">
          <button
            type="button"
            onClick={() => setViewMode('assistant')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              (viewMode as string) === 'assistant'
                ? 'bg-brand-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Conversación IA</span>
          </button>

          {hasChart && (
            <button
              type="button"
              onClick={() => setViewMode('studio')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'studio'
                  ? 'bg-brand-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Studio Visual</span>
            </button>
          )}

          {result.executive_report && (
            <button
              type="button"
              onClick={() => setViewMode('report')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'report'
                  ? 'bg-brand-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Informe</span>
            </button>
          )}

          {hasDataRows && (
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'table'
                  ? 'bg-brand-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Datos ({result.data_rows?.length || 0})</span>
            </button>
          )}
        </div>
      )}

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
        <div className="space-y-5">
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
