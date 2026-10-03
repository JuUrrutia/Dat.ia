import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useChatEngine } from '../features/chat/hooks/useChatEngine';
import { SidebarChatHistory } from '../components/chat/SidebarChatHistory';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatEmptyState } from '../components/chat/ChatEmptyState';
import { ChatPromptInput } from '../components/chat/ChatPromptInput';
import { TraceabilityModal } from '../components/traceability/TraceabilityModal';
import {
  History,
  Database,
  User as UserIcon,
  Bot,
  Tv,
  Minimize2,
  LayoutDashboard,
  AlertTriangle,
  Pin,
  Trash2,
  ExternalLink,
  X,
  Sparkles,
  BarChart3,
} from 'lucide-react';
import { queryService } from '../features/chat/services/query_service';
import { useNotifications } from '../context/NotificationContext';
import { prefersReducedMotion } from '../features/dashboard/components/charts/theme';
import { useModalA11y } from '../hooks/useModalA11y';

export const ChatDashboardPage: React.FC = () => {
  const { notify } = useNotifications();
  const {
    user,
    userRole,
    promptInput,
    setPromptInput,
    isGenerating,
    elapsedSeconds,
    longWaitNotice,
    streamingNarrative,
    activeTraceability,
    setActiveTraceability,
    isMobileHistoryOpen,
    setIsMobileHistoryOpen,
    activeDatabaseName,
    activeConnectionId,
    connectors,
    promptSuggestions,
    activeThread,
    sidebarThreads,
    threadsError,
    activeThreadId,
    pendingPrompt,
    chatBottomRef,
    searchInputRef,
    promptTextareaRef,
    handleSelectThread,
    handleNewThread,
    handleDeleteThread,
    handleSendPrompt,
    handleCancelPrompt,
    handleSelectConnection,
    handleEditPrompt,
    handleFeedback,
  } = useChatEngine();

  const [isPresentationMode, setIsPresentationMode] = useState(false);

  // Stable identities for the props that cross into ChatMessageItem.
  // elapsedSeconds ticks every second and re-renders this page; as inline
  // arrows these two were new on every render, which defeated React.memo on
  // the message list and made every chart in the thread rebuild its ECharts
  // instance once per second for the whole 8-25s of "thinking".
  const openTraceability = useCallback((trace: any) => setActiveTraceability(trace), []);
  const sendFollowUp = useCallback(
    (text: string) => {
      void handleSendPrompt(text);
    },
    [handleSendPrompt]
  );

  // Tableros Ejecutivos & Anomalías Proactivas
  // `anomaliesData` arranca en null y no en {count: 0}: null es "el servidor
  // todavía no confirmó nada". Los flags `*Loaded` / `*Error` separan los tres
  // estados (cargando / vacío real / error). Mismo patrón que `usersLoaded` en
  // useAdminUsers.
  const [widgets, setWidgets] = useState<any[]>([]);
  const [widgetsLoaded, setWidgetsLoaded] = useState(false);
  const [widgetsError, setWidgetsError] = useState<string | null>(null);
  const [isWidgetsOpen, setIsWidgetsOpen] = useState(false);

  // Dialog semantics, Escape, focus containment and focus restore.
  const widgetsModalRef = useModalA11y<HTMLDivElement>(isWidgetsOpen, () =>
    setIsWidgetsOpen(false)
  );

  // Parsed once per widgets change. The JSON.parse calls used to live inside the
  // .map callback, so they re-parsed every pinned widget's chart option and KPI
  // payload on any state change in the modal — including unpinning one, and
  // including the 1Hz elapsed-seconds tick of the page behind it.
  const parsedWidgets = useMemo(
    () =>
      widgets.map((w: any) => {
        let chartOpt: any = null;
        let kpis: any[] = [];
        try {
          if (w.chart_option_json) chartOpt = JSON.parse(w.chart_option_json);
        } catch {
          /* unparseable payload renders as "no series" instead of throwing */
        }
        try {
          if (w.kpis_json) kpis = JSON.parse(w.kpis_json);
        } catch {
          /* same */
        }
        return { w, chartOpt, kpis };
      }),
    [widgets]
  );
  const [anomaliesData, setAnomaliesData] = useState<{
    count: number;
    anomalies: any[];
    has_critical: boolean;
  } | null>(null);
  const [anomaliesError, setAnomaliesError] = useState<string | null>(null);
  const [isAnomaliesOpen, setIsAnomaliesOpen] = useState(false);

  const fetchWidgets = async () => {
    try {
      setWidgets(await queryService.getWidgets());
      setWidgetsError(null);
      setWidgetsLoaded(true);
    } catch (err: any) {
      // Sin fallback a []: la UI dice "DESCONOCIDO" en vez de "Tablero (0)".
      setWidgetsError(err.message || 'No se pudieron consultar los tableros.');
    }
  };

  const fetchAnomalies = async (connId?: number | null) => {
    try {
      setAnomaliesData(await queryService.getAnomalies(connId || undefined));
      setAnomaliesError(null);
    } catch (err: any) {
      // "No pude preguntar" no es "no hay anomalías": se descarta el dato y se
      // muestra el error.
      setAnomaliesData(null);
      setAnomaliesError(err.message || 'No se pudo consultar las anomalías.');
    }
  };

  useEffect(() => {
    fetchWidgets();
  }, []);

  useEffect(() => {
    fetchAnomalies(activeConnectionId);
  }, [activeConnectionId]);

  const handleUnpin = async (id: number) => {
    // Si el DELETE falla, el widget sigue fijado en el servidor y no puede
    // desaparecer de la pantalla.
    const ok = await queryService.unpinWidget(id);
    if (ok) {
      setWidgets((prev) => prev.filter((w) => w.id !== id));
    } else {
      notify('error', 'No se pudo desfijar el widget en el servidor; sigue fijado.');
    }
  };

  useEffect(() => {
    const handleGlobalKeys = (e: KeyboardEvent) => {
      if (e.key === 'F11') {
        e.preventDefault();
        setIsPresentationMode((prev) => !prev);
      } else if (e.key === 'Escape' && isPresentationMode) {
        setIsPresentationMode(false);
      }
    };
    window.addEventListener('keydown', handleGlobalKeys);
    return () => window.removeEventListener('keydown', handleGlobalKeys);
  }, [isPresentationMode]);

  return (
    <div className={`flex ${isPresentationMode ? 'fixed inset-0 z-50 bg-[#07090E]' : 'h-[calc(100dvh-4rem)]'} overflow-hidden bg-[#0A0D14] chat-shell`}>
      {/* Sidebar Desktop & Mobile (Hidden in Presentation Mode) */}
      {!isPresentationMode && (
        <SidebarChatHistory
          threads={sidebarThreads}
          activeId={activeThreadId}
          activeDatabaseName={activeDatabaseName}
          isOpenMobile={isMobileHistoryOpen}
          searchInputRef={searchInputRef}
          onCloseMobile={() => setIsMobileHistoryOpen(false)}
          onSelectThread={handleSelectThread}
          onNewThread={handleNewThread}
          onDeleteThread={handleDeleteThread}
        />
      )}

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative bg-gradient-to-b from-[#0B0F19] via-[#0A0D14] to-[#07090E] chat-shell-panel">
        {/* Top Context Subheader */}
        <div className="relative z-30 h-12 border-b border-[#1E293B]/60 bg-[#0F172A]/80 backdrop-blur-md px-4 flex items-center justify-between shrink-0 chat-shell-header">
          <div className="flex items-center gap-3">
            {!isPresentationMode && (
              <button
                onClick={() => setIsMobileHistoryOpen(true)}
                className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                title="Ver Historial"
              >
                <History size={18} />
              </button>
            )}

            <div className="flex items-center gap-2 text-xs font-medium">
              <Database size={14} className="text-cyan-400 shrink-0" />
              {connectors.length > 1 ? (
                <div className="flex items-center gap-1.5">
                  <label htmlFor="chat-active-db-select" className="sr-only">Seleccionar Fuente de Datos</label>
                  <select
                    id="chat-active-db-select"
                    aria-label="Seleccionar Fuente de Datos Activa"
                    value={activeConnectionId || ''}
                    onChange={(e) => handleSelectConnection(Number(e.target.value))}
                    className="bg-white dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700/80 text-slate-800 dark:text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-brand-500 cursor-pointer font-medium hover:border-slate-400 dark:hover:border-slate-600 transition-colors shadow-xs"
                  >
                    {connectors.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.db_type.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <span className="text-slate-700 dark:text-slate-300 font-semibold truncate max-w-[200px] sm:max-w-none">
                  {activeDatabaseName}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Proactive Anomalies Badge & Popover */}
            {anomaliesError && (
              <span
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border border-slate-300 dark:border-zinc-700/60 bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400"
                title={anomaliesError}
              >
                <AlertTriangle size={13} className="text-slate-400" />
                <span>Alertas: DESCONOCIDO</span>
              </span>
            )}
            {anomaliesData && anomaliesData.count > 0 && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsAnomaliesOpen((prev) => !prev)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border transition shadow-xs ${
                    anomaliesData.has_critical
                      ? 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30 hover:bg-rose-500/25'
                      : 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 hover:bg-amber-500/25'
                  }`}
                  title="Alertas y anomalías operativas"
                >
                  <AlertTriangle size={13} className={anomaliesData.has_critical ? 'text-rose-500 dark:text-rose-400' : 'text-amber-500 dark:text-amber-400'} />
                  <span>{anomaliesData.count} {anomaliesData.count === 1 ? 'Alerta' : 'Alertas'}</span>
                </button>

                {isAnomaliesOpen && (
                  <>
                    {/* Fixed invisible backdrop to dismiss popover on outside click */}
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setIsAnomaliesOpen(false)}
                    />
                    <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 shadow-2xl p-3 z-50 space-y-2 animate-fadeIn">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-zinc-800">
                        <span className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                          <AlertTriangle size={14} className="text-amber-500 dark:text-amber-400" />
                          Alertas y Monitoreo Proactivo
                        </span>
                        <button
                          type="button"
                          onClick={() => setIsAnomaliesOpen(false)}
                          className="text-gray-400 hover:text-gray-600 dark:hover:text-white"
                        >
                          <X size={14} />
                        </button>
                      </div>
                      <div className="max-h-60 overflow-y-auto space-y-2">
                        {anomaliesData.anomalies.length === 0 && (
                          <p className="p-2.5 text-[11px] text-gray-600 dark:text-zinc-400">
                            El servidor registró {anomaliesData.count} pero no devolvió el detalle.
                          </p>
                        )}
                        {anomaliesData.anomalies.map((a) => (
                          <div key={a.id} className="p-2.5 rounded-xl bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 space-y-1.5">
                            <div className="flex items-start justify-between gap-1">
                              <p className="text-xs font-semibold text-gray-800 dark:text-zinc-200">{a.title}</p>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                                a.severity === 'critical'
                                  ? 'bg-rose-500/20 text-rose-700 dark:text-rose-300'
                                  : a.severity === 'warning'
                                  ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300'
                                  : 'bg-blue-500/20 text-blue-700 dark:text-blue-300'
                              }`}>
                                {a.severity}
                              </span>
                            </div>
                            <p className="text-[11px] text-gray-600 dark:text-zinc-400">{a.description}</p>
                            <div className="flex flex-wrap items-center gap-2 pt-0.5">
                              {a.query_prompt && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setIsAnomaliesOpen(false);
                                    handleSendPrompt(a.query_prompt);
                                  }}
                                  className="inline-flex items-center gap-1 text-[10px] font-semibold text-brand-700 dark:text-brand-300 bg-brand-500/10 hover:bg-brand-500/20 dark:bg-brand-500/20 dark:hover:bg-brand-500/30 border border-brand-500/30 px-2 py-0.5 rounded transition"
                                >
                                  <span>🔍 Investigar en Chat</span>
                                </button>
                              )}
                              {a.action_route && (
                                <a
                                  href={a.action_route}
                                  className="inline-flex items-center gap-1 text-[10px] text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-200 font-medium"
                                >
                                  <span>{a.action_label || 'Ver en Admin'}</span>
                                  <ExternalLink size={10} />
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Tablero Ejecutivo Button */}
            <button
              type="button"
              onClick={() => {
                fetchWidgets();
                setIsWidgetsOpen(true);
              }}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800/60 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700/60 transition shadow-xs"
              title="Ver Tablero Ejecutivo con gráficos fijados"
            >
              <LayoutDashboard size={13} className="text-amber-500 dark:text-amber-400" />
              <span>Tablero ({widgetsError ? '?' : widgetsLoaded ? widgets.length : '…'})</span>
            </button>


            <button
              type="button"
              onClick={() => setIsPresentationMode(!isPresentationMode)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition shadow-xs ${
                isPresentationMode
                  ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/40'
                  : 'text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800/60 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700/60'
              }`}
              title="Alternar Modo Presentación Pantalla Completa (F11 / ESC)"
            >
              {isPresentationMode ? <Minimize2 size={13} /> : <Tv size={13} />}
              <span>{isPresentationMode ? 'Salir (ESC)' : 'Presentar'}</span>
            </button>
          </div>
        </div>

        {/* El historial de la barra lateral sale de localStorage; si el servidor no
            lo confirmó, se lo dice en vez de dejarlo parecer un historial verificado. */}
        {threadsError && (
          <div className="px-4 pt-2 sm:px-8">
            <p className="text-[11px] text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-2.5 py-1.5">
              {threadsError} El historial que se ve es la copia local de este navegador, sin confirmar por el servidor.
            </p>
          </div>
        )}

        {/* Scrollable Conversation Stream */}
        <div className={`flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-6 scrollbar-thin scrollbar-thumb-slate-800 ${isPresentationMode ? 'max-w-6xl mx-auto w-full' : ''}`}>
          {(!activeThread || activeThread.results.length === 0) && !pendingPrompt ? (
            <ChatEmptyState
              promptSuggestions={promptSuggestions}
              onSelectSuggestion={(sugg) => {
                setPromptInput(sugg);
                handleSendPrompt(sugg);
              }}
            />
          ) : (
            <div className={`${isPresentationMode ? 'max-w-5xl' : 'max-w-4xl'} mx-auto space-y-8`}>
              {activeThread?.results.map((res, index) => (
                <ChatMessageItem
                  key={res.id || index}
                  result={res}
                  user={user}
                  userRole={userRole}
                  activeThreadId={activeThreadId}
                  onOpenTraceability={openTraceability}
                  onEditPrompt={handleEditPrompt}
                  onFeedback={handleFeedback}
                  onFollowUp={sendFollowUp}
                />
              ))}

              {/* Pending Query: Optimistic User Message Bubble + AI Thinking Bubble */}
              {pendingPrompt && (
                <div className="space-y-4 sm:space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0 animate-fadeIn">
                  {/* User Question Bubble */}
                  <div className="flex items-start space-x-2 sm:space-x-3 justify-end">
                    <div className="chat-user-bubble bg-brand-600/15 dark:bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl shadow-md">
                      <div className="flex items-center space-x-1.5 text-[10px] text-brand-700 dark:text-brand-400 font-semibold mb-1">
                        <UserIcon className="w-3 h-3" />
                        <span>
                          {user?.username || 'Usuario'} ({userRole})
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-gray-900 dark:text-white font-medium break-words">{pendingPrompt}</p>
                    </div>
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
                      <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    </div>
                  </div>

                  {/* AI Thinking Bubble with Live Step Phases */}
                  <div className="flex items-start space-x-2 sm:space-x-3 justify-start">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-sm">
                      <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    </div>
                    <div className="chat-bot-response bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700/60 rounded-2xl rounded-tl-sm p-4 max-w-[85%] sm:max-w-2xl space-y-2.5 shadow-xl">
                      <div className="flex items-center space-x-2 text-[10px] text-brand-700 dark:text-brand-400 font-semibold">
                        <Bot className="w-3 h-3" />
                        <span>DATIA IA</span>
                        <span className="text-slate-400 dark:text-slate-500">•</span>
                        <span className="text-slate-600 dark:text-slate-400 font-normal flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
                          Procesando con IA Local
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 text-xs text-slate-700 dark:text-slate-300">
                        <span className="inline-block w-2 h-2 rounded-full bg-brand-500 dark:bg-cyan-400 animate-bounce" />
                        <span className="inline-block w-2 h-2 rounded-full bg-brand-500 dark:bg-cyan-400 animate-bounce [animation-delay:0.2s]" />
                        <span className="inline-block w-2 h-2 rounded-full bg-brand-500 dark:bg-cyan-400 animate-bounce [animation-delay:0.4s]" />
                        <span className="text-brand-700 dark:text-cyan-300 text-xs pl-1 font-medium animate-fadeIn">
                          Analizando tu pregunta con el modelo local
                        </span>
                        {/* Lo unico que el navegador sabe con certeza: que sigue
                            corriendo y cuanto lleva. Sin barra de progreso: no
                            hay forma de saber cuanto falta sin streaming. */}
                        <span className="text-[11px] text-slate-500 dark:text-slate-400 tabular-nums pl-1">
                          {elapsedSeconds}s
                        </span>
                      </div>

                      {/* Narrativa en vivo. Solo aparece cuando el modelo YA
                          produjo estos tokens: no es una animación ni una
                          estimación. Convive con el reloj (no lo reemplaza) y se
                          borra si el stream se corta, porque lo que se confirma
                          en el hilo es siempre la respuesta completa. */}
                      {streamingNarrative && (
                        <div className="mt-1 text-xs sm:text-sm leading-relaxed text-slate-700 dark:text-slate-200 whitespace-pre-wrap break-words animate-fadeIn">
                          {streamingNarrative}
                          <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-brand-500 align-text-bottom animate-pulse" />
                        </div>
                      )}

                      {longWaitNotice && (
                        <p className="text-[11px] leading-relaxed text-amber-700 dark:text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg px-2.5 py-2 animate-fadeIn">
                          La primera respuesta con un modelo local puede tardar entre 8 y 25 segundos: el motor encadena varias
                          llamadas al LLM en CPU antes de poder responder. No está colgado. Podés seguir esperando o
                          cancelar y reformular la pregunta.
                        </p>
                      )}

                      <div className="flex items-center justify-between gap-2 pt-0.5">
                        <span className="text-[10px] text-slate-500 dark:text-slate-400">
                          El motor no informa en qué etapa está hasta que responda.
                        </span>
                        <button
                          type="button"
                          onClick={handleCancelPrompt}
                          aria-label="Cancelar la consulta en curso"
                          title="Dejar de esperar. El servidor puede seguir trabajando: esto corta la espera, no el trabajo."
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[11px] font-semibold text-slate-700 dark:text-slate-300 hover:bg-rose-500/10 hover:border-rose-500/40 hover:text-rose-600 dark:hover:text-rose-400 transition-colors cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                          <span>Cancelar</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Floating Input Controls (Hidden in Presentation Mode) */}
        {!isPresentationMode && (
          <div className="p-4 md:p-6 bg-gradient-to-t from-[#07090E] via-[#0A0D14] to-transparent shrink-0 chat-shell-input-wrap">
            <div className="max-w-4xl mx-auto">
              <ChatPromptInput
                promptInput={promptInput}
                setPromptInput={setPromptInput}
                isGenerating={isGenerating}
                userRole={userRole}
                activeDatabaseName={activeDatabaseName}
                textareaRef={promptTextareaRef}
                onSubmit={(customPrompt) => handleSendPrompt(customPrompt || promptInput)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Traceability Modal */}
      <TraceabilityModal
        traceability={activeTraceability}
        isOpen={Boolean(activeTraceability)}
        onClose={() => setActiveTraceability(null)}
      />


      {/* Tablero Ejecutivo Modal */}
      {isWidgetsOpen && (
        <div ref={widgetsModalRef} role="dialog" aria-modal="true" aria-label="Tablero Ejecutivo Corporativo" tabIndex={-1} className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-5xl max-h-[85vh] flex flex-col rounded-2xl bg-white dark:bg-dark-surface border border-slate-200 dark:border-dark-border shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-dark-border flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-gray-900 dark:text-white font-bold text-base">
                <LayoutDashboard className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                <span>Tablero Ejecutivo Corporativo</span>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 bg-slate-100 dark:bg-dark-base px-2.5 py-0.5 rounded-full border border-slate-300 dark:border-dark-border ml-2">
                  {widgetsError ? 'conteo DESCONOCIDO' : widgetsLoaded ? `${widgets.length} ${widgets.length === 1 ? 'widget fijado' : 'widgets fijados'}` : 'Cargando...'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsWidgetsOpen(false)}
                className="p-1.5 rounded-xl text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-dark-card transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-zinc-700">
              {widgetsError ? (
                <div className="text-center py-16 space-y-3">
                  <Pin className="w-10 h-10 text-zinc-400 dark:text-zinc-600 mx-auto" />
                  <p className="text-slate-800 dark:text-zinc-300 font-medium text-sm">No se pudo consultar el tablero</p>
                  <p className="text-slate-500 dark:text-zinc-500 text-xs max-w-sm mx-auto">
                    {widgetsError} No se muestra un conteo de widgets porque el servidor no lo confirmó.
                  </p>
                </div>
              ) : !widgetsLoaded ? (
                <div className="text-center py-16">
                  <p className="text-slate-500 dark:text-zinc-500 text-xs">Consultando tableros fijados...</p>
                </div>
              ) : widgets.length === 0 ? (
                <div className="text-center py-16 space-y-3">
                  <Pin className="w-10 h-10 text-zinc-400 dark:text-zinc-600 mx-auto" />
                  <p className="text-slate-800 dark:text-zinc-300 font-medium text-sm">No tienes widgets fijados en el tablero</p>
                  <p className="text-slate-500 dark:text-zinc-500 text-xs max-w-sm mx-auto">
                    Haz clic en el botón <b>"Fijar en Tablero"</b> debajo de cualquier gráfico o KPI generado en el chat para anclarlo aquí.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {parsedWidgets.map(({ w, chartOpt, kpis }) => {
                    const hasChartSeries = Boolean(
                      chartOpt &&
                      Array.isArray(chartOpt.series) &&
                      chartOpt.series.length > 0 &&
                      chartOpt.series.some((s: any) => s && (Array.isArray(s.data) ? s.data.length > 0 : s.data !== undefined))
                    );

                    return (
                      <div
                        key={w.id}
                        className="rounded-2xl bg-slate-50 dark:bg-dark-base border border-slate-200 dark:border-dark-border/80 p-4 space-y-3 hover:border-brand-500/40 transition flex flex-col justify-between shadow-xs"
                      >
                        <div className="space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <h4 className="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white line-clamp-1">{w.title}</h4>
                              <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 font-mono">
                                Fijado: {new Date(w.created_at).toLocaleDateString()}
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleUnpin(w.id)}
                              className="p-1.5 rounded-lg text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer"
                              title="Quitar de tablero"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>

                          {kpis.length > 0 && (
                            <div className="grid grid-cols-2 gap-2">
                              {kpis.slice(0, 2).map((k: any, idx: number) => (
                                <div key={idx} className="p-2.5 rounded-xl bg-white dark:bg-dark-surface border border-slate-200 dark:border-dark-border">
                                  <span className="text-[10px] text-gray-600 dark:text-gray-400 truncate block">{k.title}</span>
                                  <span className="text-xs font-bold text-brand-700 dark:text-brand-300 font-mono tabular-nums truncate block mt-0.5">{k.value}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {hasChartSeries ? (
                            <div className="w-full h-44 rounded-xl overflow-hidden bg-dark-surface/80 border border-dark-border/60 p-1">
                              <ReactECharts
                                option={{
                                  ...chartOpt,
                                  animation: !prefersReducedMotion(),
                                  grid: { top: 25, right: 15, bottom: 25, left: 35, containLabel: true },
                                  tooltip: {
                                    show: true,
                                    trigger: 'axis',
                                    backgroundColor: '#0F172A',
                                    borderColor: '#334155',
                                    textStyle: { color: '#F8FAFC', fontSize: 11 },
                                  },
                                }}
                                style={{ height: '100%', width: '100%' }}
                                opts={{ renderer: 'canvas' }}
                              />
                            </div>
                          ) : (
                            <div className="w-full py-4 px-3 rounded-xl bg-dark-surface/40 border border-dashed border-dark-border/70 text-center space-y-1">
                              <BarChart3 className="w-5 h-5 text-brand-400 mx-auto opacity-70" />
                              <p className="text-[11px] text-gray-400">
                                Consulta analítica registrada. Haz clic abajo para interactuar con el gráfico y datos en vivo.
                              </p>
                            </div>
                          )}
                        </div>

                        {/* Interactive Widget Action Bar */}
                        <div className="pt-3 border-t border-dark-border/60 flex items-center justify-between gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setIsWidgetsOpen(false);
                              if (w.connection_id && w.connection_id !== activeConnectionId) {
                                handleSelectConnection(w.connection_id);
                              }
                              setPromptInput(w.query_text || w.title);
                              handleSendPrompt(w.query_text || w.title);
                            }}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 active:scale-[0.98] text-white font-semibold text-xs shadow-sm transition-all cursor-pointer"
                            title="Abrir este análisis en vivo en el chat para interactuar con datos y gráficos"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Interactuar en Chat</span>
                          </button>
                          <span className="text-[10px] text-gray-400 font-mono uppercase bg-dark-surface px-2 py-0.5 rounded border border-dark-border">
                            {w.chart_type || 'Gráfico'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
