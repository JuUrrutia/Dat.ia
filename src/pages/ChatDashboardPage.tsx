import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { QueryResult } from '../types';
import { SidebarChatHistory, ChatThread } from '../components/chat/SidebarChatHistory';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { ChatEmptyState } from '../components/chat/ChatEmptyState';
import { ChatPromptInput } from '../components/chat/ChatPromptInput';
import { TraceabilityModal } from '../components/traceability/TraceabilityModal';
import { queryService } from '../services/query_service';
import { connectorService } from '../services/connector_service';
import { History, Database, Bot, User as UserIcon } from 'lucide-react';

interface FullThread {
  id: string;
  title: string;
  timestamp: string;
  results: QueryResult[];
}

export const ChatDashboardPage: React.FC = () => {
  const { user, settings } = useAuth();
  const { notify } = useNotifications();
  const [promptInput, setPromptInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTraceability, setActiveTraceability] = useState<QueryResult['traceability'] | null>(null);
  const [isMobileHistoryOpen, setIsMobileHistoryOpen] = useState(false);
  const [activeDatabaseName, setActiveDatabaseName] = useState('BD Corporativa Local (SQLite)');
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const userRole = user?.role_name || (user?.is_admin ? 'Administrador' : 'Usuario');
  const [promptSuggestions, setPromptSuggestions] = useState<string[]>([]);

  useEffect(() => {
    let isMounted = true;
    queryService.getSuggestions(userRole).then((suggs) => {
      if (isMounted) {
        setPromptSuggestions(suggs);
      }
    });
    // Fetch active connector name
    connectorService.getConnectors().then((conns) => {
      if (isMounted && conns && conns.length > 0) {
        const active = conns.find((c) => c.is_active) || conns[0];
        setActiveDatabaseName(`${active.name} (${active.db_type.toUpperCase()})`);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [userRole]);

  // Full Threads state
  const [threads, setThreads] = useState<FullThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threads, isGenerating, activeThreadId, pendingPrompt]);

  const activeThread = threads.find((t) => t.id === activeThreadId);

  const sidebarThreads: ChatThread[] = threads.map((t) => ({
    id: t.id,
    title: t.title,
    timestamp: t.timestamp,
  }));

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
  };

  const handleNewThread = () => {
    setActiveThreadId(null);
    setPendingPrompt(null);
  };

  const handleDeleteThread = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setThreads((prev) => prev.filter((t) => t.id !== id));
    if (activeThreadId === id) {
      setActiveThreadId(null);
    }
  };

  const handleSendPrompt = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isGenerating) return;

    const currentThreadId = activeThreadId || `thread-${Date.now()}`;
    if (!activeThreadId) {
      setActiveThreadId(currentThreadId);
    }

    setPendingPrompt(trimmed);
    setIsGenerating(true);
    setPromptInput('');

    try {
      const newResult = await queryService.sendQuery(trimmed, userRole, settings);

      const vStatus = newResult.traceability?.validation_status;
      if (vStatus && vStatus !== 'APROBADO') {
        if (vStatus.includes('RECHAZADO')) {
          notify('warning', `Consulta bloqueada por AST Guardrail (${vStatus}) según perfil ${userRole}.`);
        } else if (vStatus.includes('ERROR')) {
          notify('error', `Error al procesar consulta SQL (${vStatus}).`);
        }
      }

      setThreads((prevThreads) => {
        const existing = prevThreads.find((t) => t.id === currentThreadId);
        if (existing) {
          return prevThreads.map((t) =>
            t.id === currentThreadId ? { ...t, results: [...t.results, newResult] } : t
          );
        } else {
          const newThread: FullThread = {
            id: currentThreadId,
            title: trimmed,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            results: [newResult],
          };
          return [newThread, ...prevThreads];
        }
      });
    } catch {
      // Handled in queryService fallback
    } finally {
      setPendingPrompt(null);
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-dark-base overflow-hidden">
      {/* Left Sidebar: Threads History */}
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

      {/* Main Conversation & Dashboard Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Mobile Subheader Bar with History Toggle */}
        <div className="md:hidden px-4 py-2.5 bg-dark-surface/90 border-b border-dark-border flex items-center justify-between z-10 shrink-0">
          <button
            type="button"
            onClick={() => setIsMobileHistoryOpen(true)}
            className="flex items-center space-x-1.5 text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 px-3 py-1.5 rounded-xl font-medium transition-colors"
          >
            <History className="w-3.5 h-3.5" />
            <span>Historial ({threads.length})</span>
          </button>

          <div className="flex items-center space-x-1.5 text-[11px] text-gray-400 truncate max-w-[200px]">
            <Database className="w-3 h-3 text-purple-400 shrink-0" />
            <span className="truncate font-mono">{activeDatabaseName.split(' ')[0]}</span>
          </div>
        </div>

        {/* Scrollable Conversation Thread */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-6 sm:space-y-8">
          {(activeThread && activeThread.results.length > 0) || pendingPrompt ? (
            <div className="max-w-5xl mx-auto space-y-6 sm:space-y-10 animate-fadeIn">
              {activeThread?.results.map((result, resIdx) => (
                <ChatMessageItem
                  key={result.id || resIdx}
                  result={result}
                  user={user}
                  userRole={userRole}
                  onOpenTraceability={(traceability) => setActiveTraceability(traceability)}
                />
              ))}

              {/* Optimistic Pending Message while LLM is generating */}
              {pendingPrompt && (
                <div className="space-y-4 sm:space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0 animate-fadeIn">
                  <div className="flex items-start space-x-2 sm:space-x-3 justify-end">
                    <div className="bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl">
                      <div className="flex items-center space-x-1.5 text-[10px] text-brand-400 font-semibold mb-1">
                        <UserIcon className="w-3 h-3" />
                        <span>
                          {user?.username} ({userRole})
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-white font-medium break-words">
                        {pendingPrompt}
                      </p>
                    </div>
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
                      <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    </div>
                  </div>

                  <div className="flex items-start space-x-2 sm:space-x-3 animate-fadeIn">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-500/20 animate-pulse">
                      <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    </div>

                    <div className="bg-dark-surface/90 border border-dark-border/80 rounded-2xl rounded-tl-sm p-4 space-y-2 max-w-md shadow-xl backdrop-blur-sm">
                      <div className="flex items-center space-x-2 text-xs text-brand-400 font-medium">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
                        </span>
                        <span>Procesando consulta con IA Local...</span>
                      </div>
                      <p className="text-[11px] text-gray-400 leading-relaxed">
                        Traduciendo a SQL, validando permisos RBAC y consultando base de datos activa.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>
          ) : (
            <ChatEmptyState
              promptSuggestions={promptSuggestions}
              onSelectSuggestion={(sug) => handleSendPrompt(sug)}
            />
          )}
        </div>

        {/* Input Prompt Box at Bottom */}
        <ChatPromptInput
          promptInput={promptInput}
          setPromptInput={setPromptInput}
          isGenerating={isGenerating}
          userRole={userRole}
          onSubmit={() => handleSendPrompt(promptInput)}
        />
      </div>

      {/* SQL & Governance Traceability Modal */}
      <TraceabilityModal
        isOpen={Boolean(activeTraceability)}
        traceability={activeTraceability}
        onClose={() => setActiveTraceability(null)}
      />
    </div>
  );
};
