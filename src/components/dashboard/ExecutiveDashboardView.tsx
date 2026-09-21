import React, { useState, useMemo, useEffect } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
import { ExecutiveAssistantView } from './ExecutiveAssistantView';
import { KPISection } from '../../features/dashboard/components/KPISection';
import { ChartSection } from '../../features/dashboard/components/ChartSection';
import { OfflineAlertView } from '../../features/dashboard/components/OfflineAlertView';
import { FileText, Table as TableIcon, Sparkles } from 'lucide-react';

interface ExecutiveDashboardViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
  onFollowUp?: (prompt: string) => void;
}

type ViewMode = 'assistant' | 'studio' | 'report' | 'table';

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability,
  onFollowUp,
}) => {

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
      {/* Optional Mode Switcher Tabs (Only if there are specialized alternative views like Report or Full Table) */}
      {(result.executive_report || hasDataRows) && (
        <div className="executive-dashboard-header flex items-center space-x-1.5 bg-slate-100 dark:bg-dark-base/80 p-1 rounded-xl border border-slate-200 dark:border-dark-border/80 w-fit">
          <button
            type="button"
            onClick={() => setViewMode('assistant')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewMode === 'assistant'
                ? 'bg-brand-600 text-white shadow-xs'
                : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Síntesis y Gráficos</span>
          </button>

          {result.executive_report && (
            <button
              type="button"
              onClick={() => setViewMode('report')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'report'
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white'
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
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Tabla de Datos ({result.data_rows?.length || 0})</span>
            </button>
          )}
        </div>
      )}

      {/* Main View Switching */}
      {viewMode === 'assistant' && (
        <div className="space-y-4">
          <ExecutiveAssistantView
            result={result}
            onOpenTraceability={onOpenTraceability}
            onSwitchToReport={result.executive_report ? () => setViewMode('report') : undefined}
          />

          {/* Auto-render KPIs directly under narrative if present */}
          {result.kpis && result.kpis.length > 0 && (
            <KPISection kpis={result.kpis} />
          )}

          {/* Auto-render interactive Chart directly under narrative if present */}
          {hasChart && (
            <ChartSection
              result={result}
              onDrillDown={(cat) => onFollowUp?.(`Detalla en profundidad los registros para: ${cat}`)}
              onTimeFilter={(label) => onFollowUp?.(`Filtra los datos de la consulta anterior para el periodo: ${label}`)}
            />
          )}
        </div>
      )}

      {viewMode === 'studio' && (
        <div className="space-y-5">
          <KPISection kpis={result.kpis} />
          <ChartSection
            result={result}
            onDrillDown={(cat) => onFollowUp?.(`Detalla en profundidad los registros para: ${cat}`)}
            onTimeFilter={(label) => onFollowUp?.(`Filtra los datos de la consulta anterior para el periodo: ${label}`)}
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
