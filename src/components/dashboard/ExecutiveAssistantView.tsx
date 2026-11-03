import React, { useState } from 'react';
import { QueryResult } from '../../types';
import { AssistantHeader } from '../../features/dashboard/components/assistant/AssistantHeader';
import { AssistantMarkdownBody } from '../../features/dashboard/components/assistant/AssistantMarkdownBody';
import { ShieldCheck, Brain, ChevronDown, AlertTriangle, HelpCircle, Sparkles, Trash2, BarChart3, MapPin } from 'lucide-react';
import { copyToClipboard } from '../../shared/clipboard';

interface ExecutiveAssistantViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
  onFollowUp?: (prompt: string) => void;
}

export const ExecutiveAssistantView: React.FC<ExecutiveAssistantViewProps> = ({
  result,
  onOpenTraceability,
  onSwitchToStudio,
  onSwitchToReport,
  onFollowUp,
}) => {
  const [copied, setCopied] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  const rawContent = result.conversational_response || result.summary_text || '';

  const handleCopy = () => {
    void copyToClipboard(rawContent).then((ok: boolean) => {
      if (!ok) return;
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const canSwitchToStudio = Boolean(
    result.chart_type &&
    result.chart_type !== 'none' &&
    result.data_rows &&
    result.data_rows.length > 0
  );

  return (
    <div className="w-full space-y-3 animate-fadeIn font-sans assistant-response-shell">
      <AssistantHeader
        result={result}
        canSwitchToStudio={canSwitchToStudio}
        copied={copied}
        onSwitchToStudio={onSwitchToStudio}
        onSwitchToReport={onSwitchToReport}
        onCopy={handleCopy}
      />

      {/* Main Content Area */}
      <div className="assistant-response-card light-ai-primary-card glass-panel border border-white/10 rounded-2xl p-5 sm:p-6 shadow-2xl space-y-4">
        {/* Chain-of-Thought (CoT) Reasoning Accordion (#1) */}
        {result.thinking_process && (
          <div className="rounded-xl border border-brand-500/25 bg-brand-500/5 dark:bg-brand-500/10 overflow-hidden text-xs">
            <button
              type="button"
              onClick={() => setShowThinking(!showThinking)}
              className="w-full flex items-center justify-between px-3.5 py-2 text-left font-semibold text-brand-800 dark:text-brand-300 hover:bg-brand-500/10 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Brain className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
                <span>Razonamiento analítico (Chain-of-Thought)</span>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showThinking ? 'rotate-180' : ''}`} />
            </button>
            {showThinking && (
              <div className="px-3.5 py-2.5 border-t border-brand-500/20 text-slate-700 dark:text-gray-300 whitespace-pre-wrap font-mono text-[11px] leading-relaxed bg-black/5 dark:bg-black/20">
                {result.thinking_process}
              </div>
            )}
          </div>
        )}

        {/* Narrative Analysis Body with Badges & Tooltips */}
        <AssistantMarkdownBody rawContent={rawContent} />

        {/* Proactive Null Remediation Alert Card (Option 4) */}
        {result.nulls_detected && result.nulls_detected.has_nulls && (
          <div className="rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent p-4 space-y-3 text-xs animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold text-amber-900 dark:text-amber-300">
                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                <span>Valores Nulos Detectados en {result.nulls_detected.table_name}</span>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/30">
                {result.nulls_detected.null_rows_count} filas afectadas
              </span>
            </div>
            <p className="text-slate-700 dark:text-gray-300 text-[11px] leading-relaxed">
              La consulta recuperó registros con campos nulos en las columnas:{' '}
              <strong className="text-slate-900 dark:text-white font-mono">
                {result.nulls_detected.columns_with_nulls.join(', ')}
              </strong>
              . Elige cómo deseas procesarlos para recalcular la respuesta:
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {result.nulls_detected.options.map((opt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onFollowUp?.(opt.prompt)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border shadow-xs ${
                    opt.action === 'delete_rows'
                      ? 'bg-rose-500/15 hover:bg-rose-500/25 text-rose-800 dark:text-rose-300 border-rose-500/30 hover:border-rose-500/50'
                      : opt.action === 'mode'
                      ? 'bg-purple-500/15 hover:bg-purple-500/25 text-purple-800 dark:text-purple-300 border-purple-500/30 hover:border-purple-500/50'
                      : 'bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-800 dark:text-cyan-300 border-cyan-500/30 hover:border-cyan-500/50'
                  }`}
                >
                  {opt.action === 'delete_rows' && <Trash2 className="w-3.5 h-3.5" />}
                  {opt.action === 'mode' && <BarChart3 className="w-3.5 h-3.5" />}
                  {opt.action === 'nearest' && <MapPin className="w-3.5 h-3.5" />}
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Statistical Anomalies & Causal Diagnosis (#13, #14) */}
        {result.anomalies_detected && result.anomalies_detected.length > 0 && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 dark:bg-amber-500/10 p-3.5 space-y-2.5 text-xs">
            <div className="flex items-center gap-1.5 font-bold text-amber-900 dark:text-amber-300">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <span>Anomalías Estadísticas y Diagnóstico Causal Detectado</span>
            </div>
            <div className="space-y-2">
              {result.anomalies_detected.map((anom, idx) => (
                <div key={idx} className="bg-white/70 dark:bg-zinc-900/70 p-2.5 rounded-lg border border-amber-500/20 space-y-1.5">
                  <p className="text-slate-900 dark:text-slate-100 font-medium">{anom.description}</p>
                  <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                    <strong className="text-amber-700 dark:text-amber-400">Diagnóstico:</strong> {anom.probable_cause}
                  </p>
                  {onFollowUp && (
                    <button
                      type="button"
                      onClick={() => onFollowUp(`Investiga en profundidad la anomalía detectada: ${anom.description}. ¿Cuál es la causa raíz y qué registros la explican?`)}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-200 bg-amber-500/15 hover:bg-amber-500/25 px-2 py-0.5 rounded transition mt-1"
                    >
                      <span>🔍 Investigar esta anomalía en el chat</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Proactive Ambiguity Clarification Chips (#5) */}
        {result.clarification_options && result.clarification_options.length > 0 && (
          <div className="pt-2 space-y-1.5 border-t border-slate-200/60 dark:border-dark-border/60">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300">
              <HelpCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>Opciones de aclaración rápida:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {result.clarification_options.map((opt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onFollowUp?.(opt)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 hover:bg-amber-500/20 text-amber-900 dark:text-amber-200 border border-amber-500/30 hover:border-amber-500/50 transition-all text-left shadow-2xs"
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Next Best Questions Chips (#19) */}
        {result.suggested_questions && result.suggested_questions.length > 0 && (
          <div className="pt-2 space-y-1.5 border-t border-slate-200/60 dark:border-dark-border/60">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-brand-800 dark:text-brand-300">
              <Sparkles className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
              <span>Preguntas sugeridas de profundización:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {result.suggested_questions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onFollowUp?.(q)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-500/10 hover:bg-brand-500/20 text-brand-900 dark:text-brand-200 border border-brand-500/30 hover:border-brand-500/50 transition-all text-left shadow-2xs"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer Traceability Link */}
        {onOpenTraceability && (
          <div className="pt-2 border-t border-slate-200/50 dark:border-dark-border/50 flex items-center justify-end">
            <button
              type="button"
              onClick={onOpenTraceability}
              className="flex items-center space-x-1.5 text-[11px] text-slate-500 hover:text-brand-600 dark:text-gray-400 dark:hover:text-brand-300 transition-colors font-medium cursor-pointer"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Auditoría SQL & Trazabilidad</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
