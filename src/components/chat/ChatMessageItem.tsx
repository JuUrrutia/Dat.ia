import React, { useState } from 'react';
import { User, QueryResult } from '../../types';
import { ExecutiveDashboardView } from '../dashboard/ExecutiveDashboardView';
import {
  Bot,
  User as UserIcon,
  ShieldCheck,
  Server,
  Wifi,
  WifiOff,
  Edit3,
  ThumbsUp,
  ThumbsDown,
  Code2,
  Check,
  Pin,
} from 'lucide-react';
import { queryService } from '../../features/chat/services/query_service';

interface ChatMessageItemProps {
  result: QueryResult;
  user: User | null;
  userRole: string;
  onOpenTraceability: (traceability: QueryResult['traceability']) => void;
  onEditPrompt?: (question: string) => void;
  onFeedback?: (result: QueryResult, rating: 'positive' | 'negative') => void;
  onFollowUp?: (prompt: string) => void;
}

const PipelineBadge: React.FC<{ source?: string }> = ({ source }) => {
  if (source === 'backend') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
        <Server className="w-3 h-3" />
        Backend + IA Local
      </span>
    );
  }
  if (source === 'llm_direct') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-md">
        <Wifi className="w-3 h-3" />
        LLM Directo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md">
      <WifiOff className="w-3 h-3" />
      Modo Offline
    </span>
  );
};

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  result,
  user,
  userRole,
  onOpenTraceability,
  onEditPrompt,
  onFeedback,
  onFollowUp,
}) => {
  const [copiedSql, setCopiedSql] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState<'positive' | 'negative' | null>(null);
  const [isPinned, setIsPinned] = useState(false);
  const [isPinning, setIsPinning] = useState(false);

  const handlePin = async () => {
    if (isPinned || isPinning) return;
    setIsPinning(true);
    try {
      const ok = await queryService.pinWidget({
        title: result.question,
        connection_id: (result as any).connection_id || 1,
        chart_type: result.chart_type || 'bar',
        chart_option_json: result.chart_option ? JSON.stringify(result.chart_option) : undefined,
        kpis_json: result.kpis ? JSON.stringify(result.kpis) : undefined,
        query_text: result.question,
      });
      if (ok) setIsPinned(true);
    } catch {
      // ignore
    } finally {
      setIsPinning(false);
    }
  };

  const handleCopySql = () => {
    if (result.traceability?.sql_executed) {
      navigator.clipboard.writeText(result.traceability.sql_executed);
      setCopiedSql(true);
      setTimeout(() => setCopiedSql(false), 2000);
    }
  };

  const handleSendRating = (rating: 'positive' | 'negative') => {
    setFeedbackStatus(rating);
    if (onFeedback) {
      onFeedback(result, rating);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0">
      {/* User Question Bubble */}
      <div className="flex items-start space-x-2 sm:space-x-3 justify-end group">
        <div className="bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl relative">
          <div className="flex items-center justify-between gap-4 mb-1">
            <div className="flex items-center space-x-1.5 text-[10px] text-brand-400 font-semibold">
              <UserIcon className="w-3 h-3" />
              <span>
                {user?.username} ({userRole})
              </span>
            </div>
            {onEditPrompt && (
              <button
                type="button"
                onClick={() => onEditPrompt(result.question)}
                className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-1 text-[10px] text-brand-300 hover:text-white bg-brand-500/20 hover:bg-brand-500/30 px-2 py-0.5 rounded-md border border-brand-500/30"
                title="Cargar esta pregunta en el editor para reintentar"
              >
                <Edit3 className="w-3 h-3" />
                <span>Editar</span>
              </button>
            )}
          </div>
          <p className="text-xs sm:text-sm text-white font-medium break-words">{result.question}</p>
        </div>
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
          <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
      </div>

      {/* System & Analytics Response Bubble */}
      <div className="flex items-start space-x-2 sm:space-x-3">
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-500/20">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>

        <div className="flex-1 space-y-3 sm:space-y-4 max-w-4xl min-w-0">
          {/* Badge / Status Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <PipelineBadge source={result.pipeline_source} />
            <span className="text-[10px] sm:text-[11px] text-gray-400 font-mono">{result.timestamp}</span>
            {result.traceability?.validation_status && (
              <span
                className={`inline-flex items-center gap-1 text-[9px] sm:text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                  result.traceability.validation_status.includes('APROBADO')
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                }`}
              >
                <ShieldCheck className="w-3 h-3" />
                AST: {result.traceability.validation_status}
              </span>
            )}
          </div>

          {/* Render Dynamic Dashboard Views (Report, KPIs, Charts, Tables) */}
          <ExecutiveDashboardView
            result={result}
            onOpenTraceability={() => onOpenTraceability(result.traceability)}
            onFollowUp={onFollowUp}
          />

          {/* Action Bar: Thumbs Feedback & 1-Click Copy SQL */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-dark-border/40 text-[11px] text-gray-400">
            <div className="flex items-center space-x-2">
              <span className="text-[10px] text-gray-500">¿Respuesta útil?</span>
              <button
                type="button"
                onClick={() => handleSendRating('positive')}
                className={`p-1 rounded-lg transition-colors flex items-center space-x-1 ${
                  feedbackStatus === 'positive'
                    ? 'text-emerald-400 bg-emerald-500/20 border border-emerald-500/30'
                    : 'text-gray-400 hover:text-emerald-400 hover:bg-dark-card'
                }`}
                title="Buena respuesta (reforzar en aprendizaje de IA)"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                {feedbackStatus === 'positive' && <span className="text-[10px] font-semibold">¡Registrado!</span>}
              </button>
              <button
                type="button"
                onClick={() => handleSendRating('negative')}
                className={`p-1 rounded-lg transition-colors flex items-center space-x-1 ${
                  feedbackStatus === 'negative'
                    ? 'text-rose-400 bg-rose-500/20 border border-rose-500/30'
                    : 'text-gray-400 hover:text-rose-400 hover:bg-dark-card'
                }`}
                title="Respuesta imprecisa o con errores"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                {feedbackStatus === 'negative' && <span className="text-[10px] font-semibold">Reportado</span>}
              </button>
            </div>

            <div className="flex items-center space-x-2">
              {/* Quick 1-click Pin Button */}
              {(result.chart_option || (result.kpis && result.kpis.length > 0)) && (
                <button
                  type="button"
                  onClick={handlePin}
                  disabled={isPinned || isPinning}
                  className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-medium transition-colors shadow-xs ${
                    isPinned
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                      : 'bg-dark-base hover:bg-dark-card border-dark-border/80 text-gray-300 hover:text-amber-400'
                  }`}
                  title="Fijar este gráfico/KPI en el Tablero Ejecutivo"
                >
                  <Pin className={`w-3.5 h-3.5 ${isPinned ? 'text-amber-400 fill-amber-400' : ''}`} />
                  <span>{isPinned ? 'Fijado en Tablero' : 'Fijar en Tablero'}</span>
                </button>
              )}

              {/* Quick 1-click SQL Copy Button */}
              {result.traceability?.sql_executed && (
                <button
                  type="button"
                  onClick={handleCopySql}
                  className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-dark-base hover:bg-dark-card border border-dark-border/80 text-gray-300 hover:text-white transition-colors font-medium shadow-xs"
                  title="Copiar consulta SQL ejecutada"
                >
                  {copiedSql ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400 font-semibold">¡SQL Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Copiar SQL</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

