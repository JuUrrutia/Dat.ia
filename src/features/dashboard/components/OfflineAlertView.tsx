import React from 'react';
import { QueryResult } from '../../../types';
import { ShieldAlert, AlertTriangle, ShieldCheck, Database, Lightbulb } from 'lucide-react';

interface OfflineAlertViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
}

export const OfflineAlertView: React.FC<OfflineAlertViewProps> = ({
  result,
  onOpenTraceability,
}) => {
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
    <div className={`w-full bg-gradient-to-br from-zinc-900/95 via-zinc-900/60 to-zinc-950/95 border ${borderTheme} rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6 backdrop-blur-xl animate-fadeIn`}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div className="flex items-center space-x-4">
          <div className={`w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 shadow-lg ${iconBg}`}>
            {isSecurityRejection ? (
              <ShieldAlert className="w-6 h-6" />
            ) : (
              <AlertTriangle className="w-6 h-6" />
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                {alertTitle}
              </h2>
              <span className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full border ${alertBadgeColor}`}>
                {vStatus || 'ALERTA DE SEGURIDAD'}
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              Evaluación para la consulta: <span className="text-zinc-200 font-medium">"{result.question}"</span>
            </p>
          </div>
        </div>

        {onOpenTraceability && (
          <button
            type="button"
            onClick={onOpenTraceability}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 hover:text-white transition-colors shadow-sm self-start sm:self-auto"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Inspeccionar AST</span>
          </button>
        )}
      </div>

      {/* Message Body */}
      <div className="bg-zinc-950/60 border border-white/5 rounded-2xl p-5 space-y-3">
        <div className="flex items-center space-x-2 text-xs font-bold text-amber-400">
          <Lightbulb className="w-4 h-4" />
          <span>Diagnóstico del Sistema DATIA</span>
        </div>
        <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed font-mono">
          {result.summary_text || result.traceability?.explanation || 'No se pudo completar la consulta sobre la fuente relacional.'}
        </p>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-[11px] text-zinc-400 font-mono pt-2">
        <div className="flex items-center space-x-2">
          <Database className="w-3.5 h-3.5 text-zinc-400" />
          <span>Fuente BD: {(result as any).target_database || 'SQLite Corporativo'}</span>
        </div>
        <span>Latencia: {result.traceability?.execution_time_ms || 0} ms</span>
      </div>
    </div>
  );
};
