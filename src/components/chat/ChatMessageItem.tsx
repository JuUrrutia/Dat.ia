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
  Share2,
  Star,
} from 'lucide-react';
import { queryService } from '../../features/chat/services/query_service';
import { buildDynamicChartOption, deriveProcessedRows, THEME_COLORS, ChartType } from '../dashboard/executiveDashboardUtils';

interface ChatMessageItemProps {
  result: QueryResult;
  user: User | null;
  userRole: string;
  activeThreadId?: string | null;
  onOpenTraceability: (traceability: QueryResult['traceability']) => void;
  onEditPrompt?: (question: string) => void;
  onFeedback?: (result: QueryResult, rating: 'positive' | 'negative') => void;
  onFollowUp?: (prompt: string) => void;
}

const PipelineBadge: React.FC<{ source?: string }> = ({ source }) => {
  if (source === 'backend') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 dark:bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-md">
        <Server className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
        Backend + IA Local
      </span>
    );
  }
  if (source === 'llm_direct') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-blue-700 dark:text-blue-400 bg-blue-500/15 dark:bg-blue-500/10 border border-blue-500/30 px-2 py-0.5 rounded-md">
        <Wifi className="w-3 h-3 text-blue-600 dark:text-blue-400" />
        LLM Directo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 dark:text-amber-400 bg-amber-500/15 dark:bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-md">
      <WifiOff className="w-3 h-3 text-amber-600 dark:text-amber-400" />
      Modo Offline
    </span>
  );
};

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  result,
  user,
  userRole,
  activeThreadId,
  onOpenTraceability,
  onEditPrompt,
  onFeedback,
  onFollowUp,
}) => {
  const [copiedSql, setCopiedSql] = useState(false);
  const [copiedShareLink, setCopiedShareLink] = useState(false);
  const [isGolden, setIsGolden] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState<'positive' | 'negative' | null>(null);
  const [isPinned, setIsPinned] = useState(false);
  const [isPinning, setIsPinning] = useState(false);

  const handleShareThread = () => {
    const threadId = activeThreadId || (result as any).thread_id;
    if (!threadId) return;
    const shareUrl = `${window.location.origin}${window.location.pathname}?thread=${encodeURIComponent(threadId)}`;
    navigator.clipboard.writeText(shareUrl);
    setCopiedShareLink(true);
    setTimeout(() => setCopiedShareLink(false), 2000);
  };

  const handleToggleGolden = async () => {
    if (!result.traceability?.sql_executed) return;
    const nextState = !isGolden;
    setIsGolden(nextState);
    try {
      await queryService.toggleGoldenQuery({
        question: result.question,
        sql: result.traceability.sql_executed,
        connection_id: (result as any).connection_id || 1,
        is_golden: nextState,
      });
    } catch {
      setIsGolden(!nextState);
    }
  };

  const handlePin = async () => {
    if (isPinned || isPinning) return;
    setIsPinning(true);
    try {
      let optionToSave = result.chart_option;
      if (result.data_rows && result.data_rows.length > 0) {
        const { catCol, numCol, processedRows } = deriveProcessedRows(result, 'default');
        const isCurrency = Boolean(numCol && (numCol.includes('ingreso') || numCol.includes('monto') || numCol.includes('precio') || numCol.includes('costo') || numCol.includes('total')));
        const totalVal = processedRows.reduce((sum, r) => sum + (Number(r[numCol]) || 0), 0);
        optionToSave = buildDynamicChartOption({
          processedRows,
          catCol,
          numCol,
          activeChartType: (result.chart_type as ChartType) || 'bar',
          currentTheme: THEME_COLORS.indigo,
          isCurrency,
          totalVal,
          fallbackChartOption: result.chart_option || { series: [] },
        });
      }

      const ok = await queryService.pinWidget({
        title: result.question,
        connection_id: (result as any).connection_id || 1,
        chart_type: result.chart_type || 'bar',
        chart_option_json: optionToSave ? JSON.stringify(optionToSave) : undefined,
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
        <div className="chat-user-bubble bg-brand-600/15 dark:bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl relative">
          <div className="flex items-center justify-between gap-4 mb-1">
            <div className="flex items-center space-x-1.5 text-[10px] text-brand-700 dark:text-brand-400 font-semibold">
              <UserIcon className="w-3 h-3" />
              <span>
                {user?.username} ({userRole})
              </span>
            </div>
            {onEditPrompt && (
              <button
                type="button"
                onClick={() => onEditPrompt(result.question)}
                className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-1 text-[10px] text-brand-700 dark:text-brand-300 hover:text-brand-900 dark:hover:text-white bg-brand-500/15 hover:bg-brand-500/25 px-2 py-0.5 rounded-md border border-brand-500/30"
                title="Cargar esta pregunta en el editor para reintentar"
              >
                <Edit3 className="w-3 h-3" />
                <span>Editar</span>
              </button>
            )}
          </div>
          <p className="text-xs sm:text-sm text-gray-900 dark:text-white font-medium break-words">{result.question}</p>
        </div>
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
          <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
      </div>

      {/* System & Analytics Response Bubble */}
      <div className="flex items-start space-x-2 sm:space-x-3">
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-sm">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>

        <div className="flex-1 space-y-3 sm:space-y-4 max-w-4xl min-w-0 chat-bot-response">
          {/* Badge / Status Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <PipelineBadge source={result.pipeline_source} />
            <span className="text-[10px] sm:text-[11px] text-gray-500 dark:text-gray-400 font-mono tabular-nums">{result.timestamp}</span>
            {result.traceability?.validation_status && (
              <span
                className={`inline-flex items-center gap-1 text-[9px] sm:text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                  result.traceability.validation_status.includes('APROBADO')
                    ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 dark:bg-emerald-500/10 border-emerald-500/30'
                    : 'text-rose-700 dark:text-rose-400 bg-rose-500/15 dark:bg-rose-500/10 border-rose-500/30'
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

          {/* Action Bar: Compact Icon Strip */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-dark-border/40 text-[11px] text-gray-400">
            {/* Left: Thumbs Feedback */}
            <div className="flex items-center space-x-1">
              <button
                type="button"
                onClick={() => handleSendRating('positive')}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${
                  feedbackStatus === 'positive'
                    ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/20 border border-emerald-500/30'
                    : 'text-gray-500 dark:text-gray-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-slate-100 dark:hover:bg-dark-card'
                }`}
                title="Respuesta útil (reforzar aprendizaje)"
                aria-label="Respuesta útil"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                {feedbackStatus === 'positive' && <span className="text-[10px] font-semibold">Útil</span>}
              </button>
              <button
                type="button"
                onClick={() => handleSendRating('negative')}
                className={`p-1.5 rounded-lg transition-colors flex items-center gap-1 ${
                  feedbackStatus === 'negative'
                    ? 'text-rose-700 dark:text-rose-400 bg-rose-500/20 border border-rose-500/30'
                    : 'text-gray-500 dark:text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-dark-card'
                }`}
                title="Respuesta imprecisa o con errores"
                aria-label="Respuesta imprecisa"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                {feedbackStatus === 'negative' && <span className="text-[10px] font-semibold">Reportado</span>}
              </button>
            </div>

            {/* Right: Consolidated Compact Action Group */}
            <div className="flex items-center space-x-1 bg-slate-100 dark:bg-dark-base/80 p-0.5 rounded-xl border border-slate-200 dark:border-dark-border/80">
              {/* Quick 1-click Pin Button */}
              {(result.chart_option || (result.kpis && result.kpis.length > 0)) && (
                <button
                  type="button"
                  onClick={handlePin}
                  disabled={isPinned || isPinning}
                  className={`flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                    isPinned
                      ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                      : 'text-gray-600 dark:text-gray-400 hover:text-amber-700 dark:hover:text-amber-400 hover:bg-slate-200 dark:hover:bg-dark-card'
                  }`}
                  title={isPinned ? 'Fijado en Tablero Ejecutivo' : 'Fijar en Tablero Ejecutivo'}
                  aria-label="Fijar en Tablero Ejecutivo"
                >
                  <Pin className={`w-3.5 h-3.5 ${isPinned ? 'text-amber-500 dark:text-amber-400 fill-amber-500 dark:fill-amber-400' : ''}`} />
                  <span className="hidden sm:inline text-[11px]">{isPinned ? 'Fijado' : 'Fijar'}</span>
                </button>
              )}

              {/* Quick 1-click Golden Query Toggle (Star) */}
              {result.traceability?.sql_executed && (
                <button
                  type="button"
                  onClick={handleToggleGolden}
                  className={`flex items-center space-x-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                    isGolden
                      ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                      : 'text-gray-600 dark:text-gray-400 hover:text-amber-700 dark:hover:text-amber-400 hover:bg-slate-200 dark:hover:bg-dark-card'
                  }`}
                  title={isGolden ? 'Consulta Maestra aprendida (clic para desmarcar)' : 'Marcar como Consulta Maestra'}
                  aria-label="Marcar como Consulta Maestra"
                >
                  <Star className={`w-3.5 h-3.5 ${isGolden ? 'text-amber-500 dark:text-amber-400 fill-amber-500 dark:fill-amber-400' : ''}`} />
                  <span className="hidden md:inline text-[11px]">{isGolden ? 'Maestra' : 'Hacer Maestra'}</span>
                </button>
              )}

              {/* Quick Share Query Link */}
              {activeThreadId && (
                <button
                  type="button"
                  onClick={handleShareThread}
                  className="flex items-center space-x-1 px-2 py-1 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-dark-card transition-colors text-xs font-medium"
                  title="Copiar enlace para compartir consulta"
                  aria-label="Compartir consulta"
                >
                  {copiedShareLink ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-emerald-700 dark:text-emerald-400 text-[11px]">Copiado</span>
                    </>
                  ) : (
                    <>
                      <Share2 className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                      <span className="hidden sm:inline text-[11px]">Compartir</span>
                    </>
                  )}
                </button>
              )}

              {/* Quick 1-click SQL Copy Button */}
              {result.traceability?.sql_executed && (
                <button
                  type="button"
                  onClick={handleCopySql}
                  className="flex items-center space-x-1 px-2 py-1 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-dark-card transition-colors text-xs font-medium"
                  title="Copiar consulta SQL ejecutada"
                  aria-label="Copiar SQL"
                >
                  {copiedSql ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-emerald-700 dark:text-emerald-400 text-[11px]">Copiado</span>
                    </>
                  ) : (
                    <>
                      <Code2 className="w-3.5 h-3.5 text-brand-600 dark:text-cyan-400" />
                      <span className="hidden sm:inline text-[11px]">SQL</span>
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

