import React from 'react';
import { QueryResult } from '../../../../types';
import { DataGridTable } from '../../../../components/datagrid/DataGridTable';
import { Database } from 'lucide-react';

interface AssistantSupportDataProps {
  result: QueryResult;
}

export const AssistantSupportData: React.FC<AssistantSupportDataProps> = ({ result }) => {
  if (!result.data_rows || result.data_rows.length === 0) {
    return null;
  }

  return (
    <div className="assistant-response-support bg-gradient-to-br from-white dark:from-zinc-900/90 via-slate-100 dark:via-zinc-900/60 to-slate-50 dark:to-zinc-950/90 border border-slate-200 dark:border-white/10 rounded-3xl p-6 shadow-2xl space-y-4 animate-fadeIn">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-app-text tracking-tight">
            Registros de Respaldo Extraídos de SQLite ({result.data_rows.length})
          </h3>
        </div>
        <span className="text-xs text-slate-600 dark:text-zinc-400 bg-slate-50 dark:bg-zinc-950 px-3 py-1 rounded-lg border border-white/5 font-mono">
          {result.traceability?.schema_tables_used?.join(', ') || 'SQLite'}
        </span>
      </div>
      <DataGridTable
        columns={result.data_columns}
        rows={result.data_rows}
        question={result.question}
        auditLogId={result.traceability?.audit_log_id || result.audit_log_id}
      />
    </div>
  );
};
