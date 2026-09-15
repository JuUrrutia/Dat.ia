import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../../auth/context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import { QueryResult } from '../../../types';
import { ChatThread } from '../../../components/chat/SidebarChatHistory';
import { queryService } from '../services/query_service';
import { connectorService, CorporateConnection } from '../../admin/services/connector_service';

export interface FullThread {
  id: string;
  title: string;
  timestamp: string;
  connection_id?: number;
  results: QueryResult[];
}

export function useChatEngine() {
  const { user, settings } = useAuth();
  const { notify } = useNotifications();
  const [promptInput, setPromptInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTraceability, setActiveTraceability] = useState<QueryResult['traceability'] | null>(null);
  const [isMobileHistoryOpen, setIsMobileHistoryOpen] = useState(false);
  const [activeConnectionId, setActiveConnectionId] = useState<number | null>(null);
  const [activeDatabaseName, setActiveDatabaseName] = useState('BD Corporativa Local (SQLite)');
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const promptTextareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const userRole = user?.role_name || (user?.is_admin ? 'Administrador' : 'Usuario');
  const [promptSuggestions, setPromptSuggestions] = useState<string[]>([]);
  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);

  // Local storage storage key
  const storageKey = `datia_threads_${user?.id || 'guest'}`;

  // 1. Load initial connectors & suggestions
  useEffect(() => {
    let isMounted = true;
    queryService.getSuggestions(userRole).then((suggs) => {
      if (isMounted) {
        setPromptSuggestions(suggs);
      }
    });
    connectorService.getConnectors().then((conns) => {
      if (isMounted && conns && conns.length > 0) {
        setConnectors(conns);
        const active = conns.find((c) => c.is_active) || conns[0];
        setActiveConnectionId(active.id);
        setActiveDatabaseName(`${active.name} (${active.db_type.toUpperCase()})`);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [userRole]);

  const handleSelectConnection = (id: number) => {
    const target = connectors.find((c) => c.id === id);
    if (target) {
      setActiveConnectionId(target.id);
      setActiveDatabaseName(`${target.name} (${target.db_type.toUpperCase()})`);
      notify('info', `Fuente de datos activa: ${target.name} (${target.db_type.toUpperCase()})`);
      queryService.getSuggestions(userRole).then((suggs) => {
        setPromptSuggestions(suggs);
      });
    }
  };

  // 2. Persistent Threads State (Cache-first with Backend Sync)
  const [threads, setThreads] = useState<FullThread[]>(() => {
    try {
      const cached = localStorage.getItem(storageKey);
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  // Sync threads from backend on login
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const loadBackendThreads = async () => {
      try {
        const remoteSummaries = await queryService.getThreads();
        if (remoteSummaries && remoteSummaries.length > 0 && isMounted) {
          setThreads((prev) => {
            const prevMap = new Map(prev.map((t) => [t.id, t]));
            return remoteSummaries.map((s) => ({
              id: s.id,
              title: s.title,
              timestamp: s.updated_at ? new Date(s.updated_at).toLocaleDateString() : 'Reciente',
              connection_id: s.connection_id,
              results: prevMap.get(s.id)?.results || [],
            }));
          });
        }
      } catch {
        // use local cache
      }
    };

    loadBackendThreads();
    return () => {
      isMounted = false;
    };
  }, [user, storageKey]);

  // Persist threads to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(threads));
    } catch {
      // ignore
    }
  }, [threads, storageKey]);

  // Auto-scroll on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threads, isGenerating, activeThreadId, pendingPrompt]);

  const activeThread = threads.find((t) => t.id === activeThreadId);

  const sidebarThreads: ChatThread[] = threads.map((t) => ({
    id: t.id,
    title: t.title,
    timestamp: t.timestamp,
  }));

  const handleSelectThread = async (id: string) => {
    setActiveThreadId(id);
    const target = threads.find((t) => t.id === id);
    if (target && target.results.length === 0) {
      try {
        const detail = await queryService.getThread(id);
        if (detail?.results?.length) {
          setThreads((prev) =>
            prev.map((t) => (t.id === id ? { ...t, results: detail.results } : t))
          );
        }
      } catch {
        // use existing thread state
      }
    }
  };

  const handleNewThread = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setIsGenerating(false);
    setPromptInput('');
    setPendingPrompt(null);
    setActiveTraceability(null);
    setActiveThreadId(null);
    setTimeout(() => {
      promptTextareaRef.current?.focus();
    }, 50);
  }, []);

  const handleDeleteThread = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setThreads((prev) => prev.filter((t) => t.id !== id));
    if (activeThreadId === id) {
      setActiveThreadId(null);
    }
    await queryService.deleteThread(id);
    notify('info', 'Conversación eliminada del historial.');
  };

  // Keyboard shortcuts (Ctrl+N, Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'n' || e.key === 'N')) {
        e.preventDefault();
        handleNewThread();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setIsMobileHistoryOpen(true);
        setTimeout(() => {
          searchInputRef.current?.focus();
        }, 100);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNewThread]);

  const handleEditPrompt = (question: string) => {
    setPromptInput(question);
    promptTextareaRef.current?.focus();
    notify('info', 'Pregunta cargada en el editor para reintentar.');
  };

  const handleSendPrompt = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isGenerating) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentThreadId = activeThreadId || `thread-${Date.now()}`;
    let threadTitle = trimmed.length > 32 ? `${trimmed.substring(0, 30)}...` : trimmed;

    if (!activeThreadId) {
      const newTh: FullThread = {
        id: currentThreadId,
        title: threadTitle,
        timestamp: 'Ahora',
        connection_id: activeConnectionId || 1,
        results: [],
      };
      setThreads((prev) => [newTh, ...prev]);
      setActiveThreadId(currentThreadId);
    } else if (activeThread) {
      threadTitle = activeThread.title;
    }

    // Extract multi-turn conversation history from active thread (last 2 turns)
    const conversationHistory: Array<{ question: string; sql?: string }> = [];
    if (activeThread && activeThread.results.length > 0) {
      for (const res of activeThread.results.slice(-2)) {
        conversationHistory.push({
          question: res.question,
          sql: res.traceability?.sql_executed,
        });
      }
    }

    setPendingPrompt(trimmed);
    setPromptInput('');
    setIsGenerating(true);

    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current === controller) {
        controller.abort();
        notify('warning', 'La respuesta tardó demasiado y la solicitud fue cancelada por tiempo de espera.');
      }
    }, 90000);

    try {
      const newResult = await queryService.sendQuery(
        trimmed,
        userRole,
        activeConnectionId || undefined,
        settings,
        undefined,
        conversationHistory.length > 0 ? conversationHistory : undefined
      );

      const vStatus = newResult.traceability?.validation_status;
      if (vStatus && vStatus !== 'APROBADO') {
        if (vStatus.includes('RECHAZADO')) {
          notify('warning', `Consulta bloqueada por AST Guardrail (${vStatus}) según perfil ${userRole}.`);
        } else if (vStatus.includes('ERROR')) {
          notify('error', `Error al procesar consulta SQL (${vStatus}).`);
        }
      }

      setThreads((prev) => {
        const updated = prev.map((t) => {
          if (t.id === currentThreadId) {
            const newResults = [...t.results, newResult];
            // Asynchronously save to backend
            queryService.saveThread({
              id: t.id,
              title: t.title,
              connection_id: activeConnectionId || 1,
              results: newResults,
            });
            return {
              ...t,
              results: newResults,
            };
          }
          return t;
        });
        return updated;
      });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      notify('error', err.message || 'Error al conectar con la base de datos o el motor LLM local.');
    } finally {
      clearTimeout(timeoutId);
      setIsGenerating(false);
      setPendingPrompt(null);
    }
  };

  const handleFeedback = async (
    result: QueryResult,
    rating: 'positive' | 'negative',
    comment?: string
  ) => {
    const res = await queryService.sendFeedback({
      audit_log_id: result.traceability?.audit_log_id || result.audit_log_id,
      question: result.question,
      sql: result.traceability?.sql_executed,
      connection_id: activeConnectionId || 1,
      rating,
      comment,
    });
    if (res.success) {
      notify('success', res.message);
    } else {
      notify('warning', res.message);
    }
    return res;
  };

  return {
    user,
    userRole,
    settings,
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
    threads,
    activeThreadId,
    activeThread,
    sidebarThreads,
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
  };
}

