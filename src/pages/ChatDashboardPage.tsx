import React from 'react';
import { useChatEngine } from '../features/chat/hooks/useChatEngine';
import { SidebarChatHistory } from '../components/chat/SidebarChatHistory';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatEmptyState } from '../components/chat/ChatEmptyState';
import { ChatPromptInput } from '../components/chat/ChatPromptInput';
import { TraceabilityModal } from '../components/traceability/TraceabilityModal';
import { History, Database, User as UserIcon, Bot } from 'lucide-react';

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
    handleSelectThread,
    handleNewThread,
    handleDeleteThread,
    handleSendPrompt,
    handleSelectConnection,
  } = useChatEngine();

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#0A0D14]">
      {/* Sidebar Desktop & Mobile */}
      <SidebarChatHistory
        threads={sidebarThreads}
        activeId={activeThreadId}
        activeDatabaseName={activeDatabaseName}
        isOpenMobile={isMobileHistoryOpen}
        onCloseMobile={() => setIsMobileHistoryOpen(false)}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
      />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative bg-gradient-to-b from-[#0B0F19] via-[#0A0D14] to-[#07090E]">
        {/* Top Context Subheader */}
        <div className="h-12 border-b border-[#1E293B]/60 bg-[#0F172A]/40 backdrop-blur-md px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileHistoryOpen(true)}
              className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Ver Historial"
            >
              <History size={18} />
            </button>

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
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
              Perfil: {userRole}
            </span>
          </div>
        </div>

        {/* Scrollable Conversation Stream */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-6 scrollbar-thin scrollbar-thumb-slate-800">
          {(!activeThread || activeThread.results.length === 0) && !pendingPrompt ? (
            <ChatEmptyState
              promptSuggestions={promptSuggestions}
              onSelectSuggestion={(sugg) => {
                setPromptInput(sugg);
                handleSendPrompt(sugg);
              }}
            />
          ) : (
            <div className="max-w-4xl mx-auto space-y-8">
              {activeThread?.results.map((res, index) => (
                <ChatMessageItem
                  key={res.id || index}
                  result={res}
                  user={user}
                  userRole={userRole}
                  onOpenTraceability={(trace) => setActiveTraceability(trace)}
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

        {/* Floating Input Controls */}
        <div className="p-4 md:p-6 bg-gradient-to-t from-[#07090E] via-[#0A0D14] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto">
            <ChatPromptInput
              promptInput={promptInput}
              setPromptInput={setPromptInput}
              isGenerating={isGenerating}
              userRole={userRole}
              onSubmit={() => handleSendPrompt(promptInput)}
            />
          </div>
        </div>
      </div>

      {/* Traceability Modal */}
      <TraceabilityModal
        traceability={activeTraceability}
        isOpen={Boolean(activeTraceability)}
        onClose={() => setActiveTraceability(null)}
      />
    </div>
  );
};
