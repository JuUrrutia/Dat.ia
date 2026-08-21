import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
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
  Eye,
  EyeOff,
} from 'lucide-react';

interface FullThread {
  id: string;
  title: string;
  timestamp: string;
  results: QueryResult[];
}

// Clave de respaldo para guardar conversaciones sin dependencia de usuario
const BACKUP_CHAT_KEY = 'datia_chat_history:v1:backup:all_conversations';
const SUGGESTIONS_PREFERENCE_KEY = 'datia_suggestions_enabled:v1';

const getChatHistoryKey = (user: { id?: number | string | null; username?: string | null; role_name?: string | null } | null): string => {
  const identity = user?.username ?? user?.id ?? 'anonymous';
  const role = user?.role_name ?? 'user';
  return `datia_chat_history:v1:user:${encodeURIComponent(String(identity))}:${encodeURIComponent(String(role))}`;
};

const loadUserThreads = (user: { id?: number | string | null; username?: string | null; role_name?: string | null } | null): FullThread[] => {
  try {
    const key = getChatHistoryKey(user);
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed : [];
    }
  } catch (err) {
    console.error('Error cargando threads de clave específica:', err);
  }

  // Fallback: intentar cargar desde respaldo
  try {
    const backup = localStorage.getItem(BACKUP_CHAT_KEY);
    if (backup) {
      const parsed = JSON.parse(backup);
      return Array.isArray(parsed) ? parsed : [];
    }
  } catch (err) {
    console.error('Error cargando threads de respaldo:', err);
  }

  return [];
};

const saveUserThreads = (user: { id?: number | string | null; username?: string | null; role_name?: string | null } | null, threads: FullThread[]) => {
  try {
    // Guardar en clave específica del usuario
    if (user) {
      const key = getChatHistoryKey(user);
      localStorage.setItem(key, JSON.stringify(threads));
      console.log(`✅ Guardado en clave específica: ${key}`);
    }

    // Guardar también en respaldo global
    localStorage.setItem(BACKUP_CHAT_KEY, JSON.stringify(threads));
    console.log(`✅ Guardado en respaldo global: ${BACKUP_CHAT_KEY}`);
  } catch (err) {
    console.error('❌ Error guardando threads:', err);
  }
};

const getThreadTitle = (text: string): string => {
  const clean = text.trim().replace(/\s+/g, ' ');
  if (!clean) return 'Nueva consulta';

  const lower = clean.toLowerCase();

  if (lower.includes('ventas') || lower.includes('ingresos') || lower.includes('facturación') || lower.includes('facturacion')) return 'Ventas';
  if (lower.includes('incidente') || lower.includes('ti') || lower.includes('servidor') || lower.includes('infraestructura')) return 'Incidentes TI';
  if (lower.includes('producto') || lower.includes('inventario') || lower.includes('stock')) return 'Productos';
  if (lower.includes('cliente') || lower.includes('clientes')) return 'Clientes';
  if (lower.includes('riesgo') || lower.includes('alerta') || lower.includes('seguimiento')) return 'Riesgos';
  if (lower.includes('presupuesto') || lower.includes('gasto') || lower.includes('costo') || lower.includes('costos')) return 'Costos';
  if (lower.includes('rendimiento') || lower.includes('metric') || lower.includes('kpi')) return 'Rendimiento';

  const shortened = clean.length > 38 ? `${clean.slice(0, 35).trim()}...` : clean;
  return shortened;
};

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
  const { notify } = useNotifications();
  const [promptInput, setPromptInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTraceability, setActiveTraceability] = useState<QueryResult['traceability'] | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const userRole = user?.role_name || (user?.is_admin ? 'Administrador' : 'Usuario');

  const [promptSuggestions, setPromptSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(() => {
    try {
      const saved = localStorage.getItem(SUGGESTIONS_PREFERENCE_KEY);
      return saved === null ? true : JSON.parse(saved);
    } catch {
      return true;
    }
  });

  useEffect(() => {
    let isMounted = true;
    queryService.getSuggestions(userRole).then((suggs) => {
      if (isMounted) {
        setPromptSuggestions(suggs);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [userRole]);

  // Guardar preferencia de sugerencias
  useEffect(() => {
    try {
      localStorage.setItem(SUGGESTIONS_PREFERENCE_KEY, JSON.stringify(showSuggestions));
      console.log(`✅ Preferencia de sugerencias guardada: ${showSuggestions ? 'Activadas' : 'Desactivadas'}`);
    } catch (err) {
      console.error('Error guardando preferencia de sugerencias:', err);
    }
  }, [showSuggestions]);

  // Full Threads state
  const [threads, setThreads] = useState<FullThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  // Cargar conversaciones al iniciar + sincronizar entre pestañas
  useEffect(() => {
    console.log('🔄 Cargando historial de conversaciones...');

    const loadThreads = () => {
      try {
        // Primero intenta cargar con usuario específico, sino desde respaldo
        const threadsData = loadUserThreads(user);
        setThreads(threadsData);
        console.log(`✅ ${threadsData.length} conversaciones cargadas (Usuario: ${user?.username || 'anónimo'})`);
      } catch (err) {
        console.error('❌ Error cargando conversaciones:', err);
        setThreads([]);
      }
    };

    loadThreads();

    // Escuchar cambios de localStorage desde otras pestañas/ventanas
    const handleStorageChange = (event: StorageEvent) => {
      if (
        event.key === getChatHistoryKey(user) ||
        event.key === BACKUP_CHAT_KEY
      ) {
        console.log('🔄 Cambio detectado en localStorage (otra pestaña), recargando...');
        loadThreads();
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [user?.id, user?.username]);

  // Auto-guardar threads cuando cambien
  useEffect(() => {
    if (threads.length === 0) {
      console.log('ℹ️ Sin conversaciones para guardar');
      return;
    }

    console.log(`💾 Guardando ${threads.length} conversación(es)...`);
    const saveTimer = setTimeout(() => {
      persistThreads(threads);
    }, 500); // Debounce de 500ms para evitar guardar demasiado frecuentemente

    return () => clearTimeout(saveTimer);
  }, [threads]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threads, isGenerating, activeThreadId]);

  const activeThread = threads.find((t) => t.id === activeThreadId);

  const sidebarThreads: ChatThread[] = threads.map((t) => ({
    id: t.id,
    title: t.title,
    timestamp: t.timestamp,
  }));

  const persistThreads = (nextThreads: FullThread[]) => {
    try {
      saveUserThreads(user, nextThreads);
      console.log(`✅ ${nextThreads.length} conversación(es) guardadas correctamente`);
    } catch (err) {
      console.error('❌ Error al guardar conversaciones:', err);
    }
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
  };

  const handleNewThread = () => {
    setActiveThreadId(null);
  };

  const handleDeleteThread = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setThreads((prev) => {
      const next = prev.filter((t) => t.id !== id);
      persistThreads(next);
      return next;
    });
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

      // Validar que tenemos un resultado válido
      if (!newResult || !newResult.id) {
        console.error('❌ Error: queryService no devolvió un resultado válido', newResult);
        setIsGenerating(false);
        return;
      }

      console.log('✅ Resultado de consulta recibido:', newResult.id);

      const vStatus = newResult.traceability?.validation_status;
      if (vStatus && vStatus !== 'APROBADO') {
        if (vStatus.includes('RECHAZADO')) {
          notify('warning', `Consulta bloqueada por AST Guardrail (${vStatus}) según perfil ${userRole}.`);
        } else if (vStatus.includes('ERROR')) {
          notify('error', `Error al procesar consulta SQL (${vStatus}).`);
        }
      }

      if (activeThreadId) {
        // Append to EXISTING thread
        setThreads((prevThreads) => {
          const nextThreads = prevThreads.map((thread) =>
            thread.id === activeThreadId
              ? { ...thread, results: [...thread.results, newResult] }
              : thread
          );
          // Guardar inmediatamente
          persistThreads(nextThreads);
          console.log(`✅ Resultado agregado a conversación existente: ${activeThreadId}`);
          return nextThreads;
        });
      } else {
        // Create NEW thread
        const newThreadId = `thread-${Date.now()}`;
        const newThread: FullThread = {
          id: newThreadId,
          title: getThreadTitle(text),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          results: [newResult],
        };
        
        setActiveThreadId(newThreadId);
        setThreads((prevThreads) => {
          const nextThreads = [newThread, ...prevThreads];
          // Guardar inmediatamente
          persistThreads(nextThreads);
          console.log(`✅ Nueva conversación creada: ${newThreadId}`);
          return nextThreads;
        });
      }
    } catch (error) {
      console.error('❌ Error en handleSendPrompt:', error);
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

                  {/* System & Analytics Response Bubble */}
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-500/20">
                      <Bot className="w-4 h-4" />
                    </div>

                    <div className="flex-1 space-y-4 max-w-4xl">
                      {/* Badge / Status Bar */}
                      <div className="flex items-center space-x-3">
                        <PipelineBadge source={result.pipeline_source} />
                        <span className="text-[11px] text-gray-400 font-mono">{result.timestamp}</span>
                        {result.traceability?.validation_status && (
                          <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                            result.traceability.validation_status === 'APROBADO'
                              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                              : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                          }`}>
                            <ShieldCheck className="w-3 h-3" />
                            AST: {result.traceability.validation_status}
                          </span>
                        )}
                      </div>

                      {/* Render Dynamic Dashboard Views (Report, KPIs, Charts, Tables) */}
                      <ExecutiveDashboardView
                        result={result}
                        onOpenTraceability={() => setActiveTraceability(result.traceability)}
                      />
                    </div>
                  </div>
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>
          ) : (
            /* Empty State / Welcome Screen */
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-6 p-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-xl shadow-brand-500/20 animate-bounce-subtle">
                <Sparkles className="w-8 h-8 text-white" />
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-white tracking-tight">
                  ¿Qué deseas analizar de la empresa hoy?
                </h2>
                <p className="text-xs text-gray-400 leading-relaxed max-w-md mx-auto">
                  Pregunta en lenguaje natural sobre finanzas, operaciones, incidentes o servidores. La IA local validará los permisos RBAC antes de consultar la BD corporativa.
                </p>
              </div>

              {/* Dynamic Suggestions Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl text-left">
                {promptSuggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSendPrompt(suggestion)}
                    className="p-3.5 rounded-xl bg-dark-surface hover:bg-dark-card border border-dark-border hover:border-brand-500/40 text-xs text-gray-300 hover:text-white transition-colors text-left group flex items-start space-x-2.5 shadow-sm"
                  >
                    <span className="text-brand-400 font-bold">›</span>
                    <span className="group-hover:translate-x-0.5 transition-transform">{suggestion}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Bottom Fixed Chat Input Bar */}
        <div className="p-4 border-t border-dark-border/60 bg-dark-surface/80 backdrop-blur-md space-y-3">
          {/* Suggestion Chips */}
          {showSuggestions && (
            <div className="max-w-4xl mx-auto flex items-center space-x-2 overflow-x-auto">
              <span className="text-xs text-gray-400 font-medium shrink-0 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-brand-400" /> Sugerencias de Busqueda:
              </span>
              {promptSuggestions.map((sug) => (
                <button
                  key={sug}
                  onClick={() => handleSendPrompt(sug)}
                  className="text-xs text-gray-300 bg-dark-base hover:bg-dark-card border border-dark-border hover:border-brand-500/30 rounded-lg px-3 py-1 whitespace-nowrap transition-colors hover:text-white"
                >
                  {sug}
                </button>
              ))}
            </div>
          )}

          {/* Prompt Input Form */}
          <div className="max-w-4xl mx-auto relative flex items-center gap-2">
            <input
              type="text"
              value={promptInput}
              onChange={(e) => setPromptInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt(promptInput)}
              disabled={isGenerating}
              placeholder={`Pregunta a Datia sobre los datos corporativos (${userRole})...`}
              aria-label="Pregunta analítica"
              className="flex-1 bg-dark-base border border-dark-border rounded-xl pl-4 pr-12 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors shadow-inner"
            />

            <button
              onClick={() => setShowSuggestions(!showSuggestions)}
              aria-label={showSuggestions ? 'Desactivar sugerencias' : 'Activar sugerencias'}
              title={showSuggestions ? 'Desactivar sugerencias' : 'Activar sugerencias'}
              className="p-2 rounded-lg border border-dark-border hover:border-brand-500/30 text-gray-400 hover:text-brand-400 transition-colors"
            >
              {showSuggestions ? (
                <Eye className="w-4 h-4" />
              ) : (
                <EyeOff className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={() => handleSendPrompt(promptInput)}
              disabled={isGenerating || !promptInput.trim()}
              aria-label="Enviar consulta"
              className="p-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white disabled:opacity-40 transition-colors shadow-md shadow-brand-600/30"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
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
