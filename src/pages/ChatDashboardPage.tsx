import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { QueryResult } from '../types';
import { SidebarChatHistory, ChatThread } from '../components/chat/SidebarChatHistory';
import { InteractiveChart } from '../components/dashboard/InteractiveChart';
import { ExecutiveDashboardView } from '../components/dashboard/ExecutiveDashboardView';
import { DataGridTable } from '../components/datagrid/DataGridTable';
import { TraceabilityModal } from '../components/traceability/TraceabilityModal';
import { queryService } from '../services/query_service';
import {
  Send,
  Sparkles,
  TrendingUp,
  ShieldCheck,
  BarChart3,
  Bot,
  User as UserIcon,
  Server,
  Wifi,
  WifiOff,
} from 'lucide-react';

interface FullThread {
  id: string;
  title: string;
  timestamp: string;
  results: QueryResult[];
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

export const ChatDashboardPage: React.FC = () => {
  const { user, settings } = useAuth();
  const [promptInput, setPromptInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTraceability, setActiveTraceability] = useState<QueryResult['traceability'] | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const userRole = user?.role_name || (user?.is_admin ? 'Administrador' : 'Usuario');

  // Role-specific suggestion chips
  const getSuggestionsForRole = () => {
    if (userRole === 'TI') {
      return [
        'Incidentes de TI por servidor y nivel de prioridad',
        'Métricas de consumo de CPU y RAM por servidor',
        'Detalle de servidores e IP de infraestructura'
      ];
    }
    if (userRole === 'Usuario') {
      return [
        '¿Qué información puedo consultar con mi perfil Usuario?',
        '¿Cómo solicito acceso a los dominios Economía o TI?'
      ];
    }
    // Economista & Admin
    return [
      '¿Cuáles fueron los ingresos del Q3 por categoría?',
      'Top 5 clientes con mayor volumen de compras',
      'Evolución mensual de ventas y costos operacionales'
    ];
  };

  const promptSuggestions = getSuggestionsForRole();

  // Full Threads state
  const [threads, setThreads] = useState<FullThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threads, isGenerating, activeThreadId]);

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
  };

  const handleDeleteThread = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setThreads((prev) => prev.filter((t) => t.id !== id));
    if (activeThreadId === id) {
      setActiveThreadId(null);
    }
  };

  const handleSendPrompt = async (text: string) => {
    if (!text.trim()) return;

    setIsGenerating(true);
    setPromptInput('');

    try {
      const newResult = await queryService.sendQuery(text, userRole, settings);

      setThreads((prevThreads) => {
        if (activeThreadId) {
          // Append to EXISTING thread
          return prevThreads.map((thread) => {
            if (thread.id === activeThreadId) {
              return {
                ...thread,
                results: [...thread.results, newResult],
              };
            }
            return thread;
          });
        } else {
          // Create NEW thread
          const newThread: FullThread = {
            id: `thread-${Date.now()}`,
            title: text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            results: [newResult],
          };
          setActiveThreadId(newThread.id);
          return [newThread, ...prevThreads];
        }
      });
    } catch {
      // Handled in queryService fallback
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-dark-base overflow-hidden">
      {/* Left Sidebar: ChatGPT-style Threads History */}
      <SidebarChatHistory
        threads={sidebarThreads}
        activeId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
      />

      {/* Main Conversation & Dashboard Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Scrollable Conversation Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {activeThread && activeThread.results.length > 0 ? (
            <div className="max-w-5xl mx-auto space-y-10 animate-fadeIn">
              {activeThread.results.map((result, resIdx) => (
                <div key={result.id || resIdx} className="space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0">
                  {/* User Question Bubble */}
                  <div className="flex items-start space-x-3 justify-end">
                    <div className="bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-4 max-w-2xl">
                      <div className="flex items-center space-x-2 text-[10px] text-brand-400 font-semibold mb-1">
                        <UserIcon className="w-3 h-3" />
                        <span>{user?.username} ({userRole})</span>
                      </div>
                      <p className="text-sm text-white font-medium">{result.question}</p>
                    </div>
                    <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
                      <UserIcon className="w-4 h-4" />
                    </div>
                  </div>

                  {/* AI Response Card */}
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-700 flex items-center justify-center text-zinc-950 shrink-0 shadow-lg shadow-amber-500/20 font-bold">
                      <Bot className="w-4 h-4" />
                    </div>

                    <div className="flex-1 space-y-4">
                      {/* Compact Badge Bar */}
                      <div className="flex items-center justify-between bg-zinc-950/60 border border-white/5 rounded-2xl px-4 py-2">
                        <div className="flex items-center space-x-2">
                          <PipelineBadge source={result.pipeline_source} />
                          <span className="text-[11px] text-zinc-400 font-medium">
                            Procesado en {result.traceability?.execution_time_ms || 0} ms
                          </span>
                        </div>

                        <button
                          onClick={() => setActiveTraceability(result.traceability)}
                          className="flex items-center space-x-1.5 text-xs text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 px-3 py-1 rounded-lg transition-all"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Auditar SQL & AST</span>
                        </button>
                      </div>

                      {/* Executive Dashboard View (Studio, Report, Dataset) */}
                      <ExecutiveDashboardView
                        result={result}
                        onOpenTraceability={() => setActiveTraceability(result.traceability)}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Welcome Empty State when starting a new chat */
            <div className="max-w-2xl mx-auto text-center py-16 space-y-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-500 shadow-xl shadow-brand-500/20">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                ¿En qué puedo ayudarte hoy en el perfil {userRole}?
              </h2>
              <p className="text-xs text-gray-400">
                Selecciona una de las sugerencias activas abajo o escribe una pregunta para consultar la base de datos corporativa.
              </p>
            </div>
          )}

          {/* Loading Indicator */}
          {isGenerating && (
            <div className="max-w-5xl mx-auto flex items-start space-x-3">
              <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 animate-bounce">
                <Bot className="w-4 h-4" />
              </div>
              <div className="glass-panel rounded-2xl p-6 border border-brand-500/30 w-full text-center space-y-3">
                <div className="inline-flex items-center space-x-2 text-brand-400 text-xs font-semibold">
                  <Sparkles className="w-4 h-4 animate-spin" />
                  <span>Consultando demo_corporativa.db & Validando AST...</span>
                </div>
                <p className="text-xs text-gray-400">Invocando LLM Local → Recortando Esquema → Ejecutando SQL READ ONLY</p>
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Bottom Fixed Chat Input Bar */}
        <div className="p-4 border-t border-dark-border/60 bg-dark-surface/80 backdrop-blur-md space-y-3">
          {/* Suggestion Chips */}
          <div className="max-w-4xl mx-auto flex items-center space-x-2 overflow-x-auto">
            <span className="text-xs text-gray-400 font-medium shrink-0 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" /> Sugerencias Activas:
            </span>
            {promptSuggestions.map((sug, i) => (
              <button
                key={i}
                onClick={() => handleSendPrompt(sug)}
                className="text-xs text-gray-300 bg-dark-base hover:bg-dark-card border border-dark-border hover:border-brand-500/30 rounded-lg px-3 py-1 whitespace-nowrap transition-all hover:text-white"
              >
                {sug}
              </button>
            ))}
          </div>

          {/* Prompt Input Form */}
          <div className="max-w-4xl mx-auto relative flex items-center">
            <input
              type="text"
              value={promptInput}
              onChange={(e) => setPromptInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt(promptInput)}
              placeholder="Haz una pregunta sobre tus datos o pulsa una sugerencia..."
              className="w-full bg-dark-base border border-dark-border rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all shadow-inner"
            />
            <button
              onClick={() => handleSendPrompt(promptInput)}
              disabled={isGenerating || !promptInput.trim()}
              className="absolute right-2 p-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white disabled:opacity-40 transition-all shadow-md shadow-brand-600/30"
            >
              {isGenerating ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Traceability Modal */}
      {activeTraceability && (
        <TraceabilityModal
          traceability={activeTraceability}
          isOpen={!!activeTraceability}
          onClose={() => setActiveTraceability(null)}
        />
      )}
    </div>
  );
};
