import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { queryService } from '../features/chat/services/query_service';

export const ChatDashboardPage: React.FC = () => {
  const {
    user,
    userRole,
    promptInput,
    setPromptInput,
    isGenerating,
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
    activeThreadId,
    pendingPrompt,
    chatBottomRef,
    searchInputRef,
    promptTextareaRef,
    handleSelectThread,
    handleNewThread,
    handleDeleteThread,
    handleSendPrompt,
    handleSelectConnection,
    handleEditPrompt,
    handleFeedback,
  } = useChatEngine();

  const [isPresentationMode, setIsPresentationMode] = useState(false);

  // Tableros Ejecutivos & Anomalías Proactivas
  const [widgets, setWidgets] = useState<any[]>([]);
  const [isWidgetsOpen, setIsWidgetsOpen] = useState(false);
  const [anomaliesData, setAnomaliesData] = useState<{
    count: number;
    anomalies: any[];
    has_critical: boolean;
  }>({ count: 0, anomalies: [], has_critical: false });
  const [isAnomaliesOpen, setIsAnomaliesOpen] = useState(false);

  const fetchWidgets = async () => {
    const list = await queryService.getWidgets();
    setWidgets(list);
  };

  const fetchAnomalies = async () => {
    const data = await queryService.getAnomalies();
    setAnomaliesData(data);
  };

  useEffect(() => {
    fetchWidgets();
    fetchAnomalies();
  }, []);

  const handleUnpin = async (id: number) => {
    await queryService.unpinWidget(id);
    setWidgets((prev) => prev.filter((w) => w.id !== id));
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
    <div className={`flex ${isPresentationMode ? 'fixed inset-0 z-50 bg-[#07090E]' : 'h-[calc(100vh-64px)]'} overflow-hidden bg-[#0A0D14]`}>
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
      <div className="flex-1 flex flex-col min-w-0 h-full relative bg-gradient-to-b from-[#0B0F19] via-[#0A0D14] to-[#07090E]">
        {/* Top Context Subheader */}
        <div className="h-12 border-b border-[#1E293B]/60 bg-[#0F172A]/40 backdrop-blur-md px-4 flex items-center justify-between shrink-0">
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
                    className="bg-slate-900/90 border border-slate-700/80 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-cyan-500/60 cursor-pointer font-medium hover:border-slate-600 transition-colors"
                  >
                    {connectors.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.db_type.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <span className="text-slate-300 font-semibold truncate max-w-[200px] sm:max-w-none">
                  {activeDatabaseName}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Proactive Anomalies Badge & Popover */}
            {anomaliesData.count > 0 && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsAnomaliesOpen((prev) => !prev)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
                    anomaliesData.has_critical
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 hover:bg-rose-500/30'
                      : 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                  }`}
                  title="Alertas y anomalías operativas"
                >
                  <AlertTriangle size={13} className={anomaliesData.has_critical ? 'text-rose-400' : 'text-amber-400'} />
                  <span>{anomaliesData.count} {anomaliesData.count === 1 ? 'Alerta' : 'Alertas'}</span>
                </button>

                {isAnomaliesOpen && (
                  <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-zinc-900 border border-zinc-700 shadow-2xl p-3 z-40 space-y-2 animate-fadeIn">
                    <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                      <span className="text-xs font-bold text-white flex items-center gap-1.5">
                        <AlertTriangle size={14} className="text-amber-400" />
                        Alertas y Monitoreo Proactivo
                      </span>
                      <button
                        type="button"
                        onClick={() => setIsAnomaliesOpen(false)}
                        className="text-zinc-400 hover:text-white"
                      >
                        <X size={14} />
                      </button>
                    </div>
                    <div className="max-h-60 overflow-y-auto space-y-2">
                      {anomaliesData.anomalies.map((a) => (
                        <div key={a.id} className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-1">
                          <p className="text-xs font-semibold text-zinc-200">{a.title}</p>
                          <p className="text-[11px] text-zinc-400">{a.description}</p>
                          {a.action_route && (
                            <a
                              href={a.action_route}
                              className="inline-flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 font-medium mt-1"
                            >
                              <span>{a.action_label}</span>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
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
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition"
              title="Ver Tablero Ejecutivo con gráficos fijados"
            >
              <LayoutDashboard size={13} className="text-amber-400" />
              <span>Tablero ({widgets.length})</span>
            </button>


            <button
              type="button"
              onClick={() => setIsPresentationMode(!isPresentationMode)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                isPresentationMode
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60'
              }`}
              title="Alternar Modo Presentación Pantalla Completa (F11 / ESC)"
            >
              {isPresentationMode ? <Minimize2 size={13} /> : <Tv size={13} />}
              <span>{isPresentationMode ? 'Salir (ESC)' : 'Presentar'}</span>
            </button>

            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
              Perfil: {userRole}
            </span>
          </div>
        </div>

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
                  onOpenTraceability={(trace) => setActiveTraceability(trace)}
                  onEditPrompt={handleEditPrompt}
                  onFeedback={handleFeedback}
                  onFollowUp={(text) => handleSendPrompt(text)}
                />
              ))}

              {/* Pending Query: Optimistic User Message Bubble + AI Thinking Bubble */}
              {pendingPrompt && (
                <div className="space-y-4 sm:space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0 animate-fadeIn">
                  {/* User Question Bubble */}
                  <div className="flex items-start space-x-2 sm:space-x-3 justify-end">
                    <div className="bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl shadow-md">
                      <div className="flex items-center space-x-1.5 text-[10px] text-brand-400 font-semibold mb-1">
                        <UserIcon className="w-3 h-3" />
                        <span>
                          {user?.username || 'Usuario'} ({userRole})
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-white font-medium break-words">{pendingPrompt}</p>
                    </div>
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
                      <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    </div>
                  </div>

                  {/* AI Thinking Bubble */}
                  <div className="flex items-start space-x-2 sm:space-x-3 justify-start">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-cyan-600/20">
                      <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-pulse" />
                    </div>
                    <div className="bg-slate-900/90 border border-slate-700/60 rounded-2xl rounded-tl-sm p-4 max-w-[85%] sm:max-w-2xl space-y-2.5 shadow-xl">
                      <div className="flex items-center space-x-2 text-[10px] text-cyan-400 font-semibold">
                        <Bot className="w-3 h-3" />
                        <span>DATIA IA</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-400 font-normal flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                          Traduciendo a SQL con IA Local...
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 text-xs text-slate-300">
                        <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-bounce" />
                        <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.2s]" />
                        <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.4s]" />
                        <span className="text-slate-400 text-xs pl-1">
                          Generando consulta SQL y preparando visualizaciones...
                        </span>
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
          <div className="p-4 md:p-6 bg-gradient-to-t from-[#07090E] via-[#0A0D14] to-transparent shrink-0">
            <div className="max-w-4xl mx-auto">
              <ChatPromptInput
                promptInput={promptInput}
                setPromptInput={setPromptInput}
                isGenerating={isGenerating}
                userRole={userRole}
                activeDatabaseName={activeDatabaseName}
                textareaRef={promptTextareaRef}
                onSubmit={() => handleSendPrompt(promptInput)}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-5xl max-h-[85vh] flex flex-col rounded-3xl bg-zinc-900 border border-zinc-700 shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <LayoutDashboard className="w-5 h-5 text-amber-400" />
                <span>Tablero Ejecutivo Corporativo</span>
                <span className="text-xs font-medium text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded-full ml-2">
                  {widgets.length} {widgets.length === 1 ? 'widget fijado' : 'widgets fijados'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsWidgetsOpen(false)}
                className="p-1.5 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-zinc-700">
              {widgets.length === 0 ? (
                <div className="text-center py-16 space-y-3">
                  <Pin className="w-10 h-10 text-zinc-600 mx-auto" />
                  <p className="text-zinc-300 font-medium text-sm">No tienes widgets fijados en el tablero</p>
                  <p className="text-zinc-500 text-xs max-w-sm mx-auto">
                    Haz clic en el botón <b>"Fijar en Tablero"</b> debajo de cualquier gráfico o KPI generado en el chat para anclarlo aquí.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {widgets.map((w) => {
                    let chartOpt = null;
                    let kpis: any[] = [];
                    try {
                      if (w.chart_option_json) chartOpt = JSON.parse(w.chart_option_json);
                    } catch {}
                    try {
                      if (w.kpis_json) kpis = JSON.parse(w.kpis_json);
                    } catch {}

                    return (
                      <div
                        key={w.id}
                        className="rounded-2xl bg-zinc-950 border border-zinc-800/80 p-4 space-y-3 hover:border-zinc-700 transition flex flex-col"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h4 className="text-xs sm:text-sm font-semibold text-white line-clamp-1">{w.title}</h4>
                            <p className="text-[10px] text-zinc-500 mt-0.5 font-mono">
                              Fijado: {new Date(w.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleUnpin(w.id)}
                            className="p-1 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
                            title="Quitar de tablero"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        {kpis.length > 0 && (
                          <div className="grid grid-cols-2 gap-2">
                            {kpis.slice(0, 2).map((k: any, idx: number) => (
                              <div key={idx} className="p-2 rounded-xl bg-zinc-900 border border-zinc-800">
                                <span className="text-[10px] text-zinc-400 truncate block">{k.title}</span>
                                <span className="text-xs font-bold text-indigo-300 truncate block">{k.value}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {chartOpt && (
                          <div className="w-full h-44 rounded-xl overflow-hidden bg-zinc-900/50">
                            <ReactECharts
                              option={{ ...chartOpt, animation: false }}
                              style={{ height: '100%', width: '100%' }}
                              opts={{ renderer: 'canvas' }}
                            />
                          </div>
                        )}
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
