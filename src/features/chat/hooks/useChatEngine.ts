import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import { QueryResult } from '../../../types';
import { ChatThread } from '../../../components/chat/SidebarChatHistory';
import { queryService } from '../services/query_service';
import { connectorService, CorporateConnection } from '../../../services/connector_service';

export interface FullThread {
  id: string;
  title: string;
  timestamp: string;
  results: QueryResult[];
}

const CHAT_THREADS_KEY_PREFIX = 'datia_chat_threads:v1:';
const CHAT_SUGGESTIONS_KEY_PREFIX = 'datia_chat_suggestions:v1:';

const loadThreads = (userId: number): FullThread[] => {
  try {
    const saved = localStorage.getItem(`${CHAT_THREADS_KEY_PREFIX}${userId}`);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
};

const loadSuggestionsPreference = (userId: number): boolean => {
  try {
    const saved = localStorage.getItem(`${CHAT_SUGGESTIONS_KEY_PREFIX}${userId}`);
    return saved === null ? true : saved === 'true';
  } catch {
    return true;
  }
};

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

  const userRole = user?.role_name || (user?.is_admin ? 'Administrador' : 'Usuario');
  const [promptSuggestions, setPromptSuggestions] = useState<string[]>([]);
  const [showPromptSuggestions, setShowPromptSuggestions] = useState(() => (
    user ? loadSuggestionsPreference(user.id) : true
  ));

  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);

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

  const [threads, setThreads] = useState<FullThread[]>(() => (user ? loadThreads(user.id) : []));
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const isHydratingThreadsRef = useRef(false);

  useEffect(() => {
    if (!user) {
      setThreads([]);
      setActiveThreadId(null);
      setShowPromptSuggestions(true);
      return;
    }

    isHydratingThreadsRef.current = true;
    setThreads(loadThreads(user.id));
    setActiveThreadId(null);
    setShowPromptSuggestions(loadSuggestionsPreference(user.id));
  }, [user?.id]);

  const togglePromptSuggestions = () => {
    setShowPromptSuggestions((previous) => {
      const next = !previous;
      if (user) {
        try {
          localStorage.setItem(`${CHAT_SUGGESTIONS_KEY_PREFIX}${user.id}`, String(next));
        } catch {
          // Ignore storage failures; the preference remains active for this session.
        }
      }
      return next;
    });
  };

  useEffect(() => {
    if (!user) return;
    if (isHydratingThreadsRef.current) {
      isHydratingThreadsRef.current = false;
      return;
    }

    try {
      localStorage.setItem(`${CHAT_THREADS_KEY_PREFIX}${user.id}`, JSON.stringify(threads));
    } catch {
      // Ignore storage failures; the in-memory history remains available.
    }
  }, [threads, user?.id]);

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

  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSendPrompt = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isGenerating) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentThreadId = activeThreadId || `thread-${Date.now()}`;
    if (!activeThreadId) {
      const newTh: FullThread = {
        id: currentThreadId,
        title: trimmed.length > 32 ? `${trimmed.substring(0, 30)}...` : trimmed,
        timestamp: 'Ahora',
        results: [],
      };
      setThreads((prev) => [newTh, ...prev]);
      setActiveThreadId(currentThreadId);
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
      const newResult = await queryService.sendQuery(trimmed, userRole, activeConnectionId || undefined, settings);

      const vStatus = newResult.traceability?.validation_status;
      if (vStatus && vStatus !== 'APROBADO') {
        if (vStatus.includes('RECHAZADO')) {
          notify('warning', `Consulta bloqueada por AST Guardrail (${vStatus}) según perfil ${userRole}.`);
        } else if (vStatus.includes('ERROR')) {
          notify('error', `Error al procesar consulta SQL (${vStatus}).`);
        }
      }

      setThreads((prev) =>
        prev.map((t) => {
          if (t.id === currentThreadId) {
            return {
              ...t,
              results: [...t.results, newResult],
            };
          }
          return t;
        })
      );
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      notify('error', err.message || 'Error al conectar con la base de datos o el motor LLM local.');
    } finally {
      clearTimeout(timeoutId);
      setIsGenerating(false);
      setPendingPrompt(null);
    }
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
    showPromptSuggestions,
    togglePromptSuggestions,
    threads,
    activeThreadId,
    activeThread,
    sidebarThreads,
    pendingPrompt,
    chatBottomRef,
    handleSelectThread,
    handleNewThread,
    handleDeleteThread,
    handleSendPrompt,
    handleSelectConnection,
  };
}
