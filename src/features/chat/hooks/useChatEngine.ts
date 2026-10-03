import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../../auth/context/AuthContext';
import { useNotifications } from '../../../context/NotificationContext';
import { QueryResult } from '../../../types';
import { ChatThread } from '../../../components/chat/SidebarChatHistory';
import { queryService } from '../services/query_service';
import { connectorService, CorporateConnection } from '../../admin/services/connector_service';

// El motor encadena hasta 3 llamadas al LLM en CPU (clasificar intencion ->
// recuperar esquema -> generar SQL) mas la validacion y la ejecucion. Medido en
// este equipo: 8 s el mejor caso, 25 s lo tipico de una pregunta con analisis.
// A los 8 s el usuario ya se esta preguntando si se colgo, y ese es el momento
// de decirle por que sigue esperando. Antes de 8 s no dice nada: menos de 8 s de
// espera no se percibe como colgado.
export const LONG_WAIT_NOTICE_SECONDS = 8;

// Corta la espera del cliente a los 90 s. El servidor puede seguir trabajando:
// el AbortController corta la espera, no deshace el trabajo del backend.
const REQUEST_TIMEOUT_MS = 90_000;

// Cuantos hilos caben en la COPIA LOCAL del historial. Es un tope de
// persistencia, no de pantalla: `threads` en memoria nunca se poda, asi que
// recorta el snapshot y jamas lo que el usuario tiene a la vista.
// El corte va por la cabeza porque el array ya viene ordenado del mas reciente
// al mas viejo (aca los nuevos se anteponen; el servidor los devuelve con
// `order_by(updated_at.desc())`), y lo que pesa son las filas: cada `QueryResult`
// arrastra `data_rows` de la BD del cliente dentro del snapshot.
// ponytail: techo de 50 hilos en localStorage; los descartados sobreviven en el
// servidor (saveThread los POSTea) y `handleSelectThread` los rehidrata al
// hacer clic. Subir el tope, o vaciar `data_rows` y guardar solo la metadata de
// las filas, si el historial local llegara a pesar.
const PERSISTED_THREADS_LIMIT = 50;

// Ventana de agrupado del stream. Los deltas llegan token por token y cada
// `setState` re-renderiza el arbol entero del dashboard: escribir cada uno es
// un render por token. Volcar cada ~80 ms deja el texto creciendo a la vista
// (12 actualizaciones por segundo es indistinguible de token a token para el
// ojo) y baja el render de O(tokens) a O(ventana). Intervalo y no
// `requestAnimationFrame`: con la pestana en background el rAF se congela y la
// narrativa se frena hasta que vuelve el foco, y en ese rato no hay nada que
// mirar.
const STREAM_FLUSH_MS = 80;

// `localStorage` no da un codigo unico de cuota agotada, pero si un nombre
// consistente: `QuotaExceededError` en los navegadores modernos,
// `NS_ERROR_DOM_QUOTA_REACHED` (y codigos 22/1014) en los viejos. Antes esto
// terminaba en un `catch { // ignore }` y el historial local dejaba de guardarse
// sin decir una sola palabra.
const isQuotaError = (err: unknown): boolean => {
  const e = err as { name?: string; code?: number } | null;
  return (
    e?.name === 'QuotaExceededError' ||
    e?.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
    e?.code === 22 ||
    e?.code === 1014
  );
};

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

  // Secuencia de sugerencias: la ultima peticion gana. Sin esto, la respuesta
  // del conector anterior (o del montaje) puede llegar tarde y pisar la lista
  // que corresponde al conector que el usuario tiene en pantalla.
  const suggestionsSeqRef = useRef(0);

  const loadSuggestions = useCallback((connectionId?: number) => {
    const seq = ++suggestionsSeqRef.current;
    queryService.getSuggestions(connectionId).then((suggs) => {
      if (seq === suggestionsSeqRef.current) {
        setPromptSuggestions(suggs);
      }
    });
  }, []);

  // 1. Load initial connectors & suggestions
  useEffect(() => {
    let isMounted = true;
    loadSuggestions();
    connectorService.getConnectors().then((conns) => {
      if (isMounted && conns && conns.length > 0) {
        setConnectors(conns);
        const active = conns.find((c) => c.is_active) || conns[0];
        setActiveConnectionId(active.id);
        setActiveDatabaseName(`${active.name} (${active.db_type.toUpperCase()})`);
        loadSuggestions(active.id);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [loadSuggestions]);

  const handleSelectConnection = useCallback((id: number) => {
    const target = connectors.find((c) => c.id === id);
    if (target) {
      setActiveConnectionId(target.id);
      setActiveDatabaseName(`${target.name} (${target.db_type.toUpperCase()})`);
      notify('info', `Fuente de datos activa: ${target.name} (${target.db_type.toUpperCase()})`);
      loadSuggestions(target.id);
    }
  }, [connectors, loadSuggestions, notify]);

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
  // Mismo par que usa useAdminUsers: `threadsLoaded` separa "todavia cargando"
  // de "la API devolvio []" y `threadsError` de "no se pudo preguntar". Antes
  // un fallo de red dejaba el cache local en pantalla indistinguible de un
  // historial confirmado por el servidor.
  const [threadsLoaded, setThreadsLoaded] = useState(false);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  // Segundos que lleva la consulta en curso. Es lo unico que el frontend puede
  // afirmar con certeza sin SSE: que sigue corriendo y cuanto lleva. Antes se
  // mostraba una "fase" que avanzaba por tiempos fijos (1400/3200/5500 ms) y
  // decia "Ejecutando consulta en base de datos" a los 3,2 s sin saber si el
  // motor estaba classifying, generando SQL o esperando al LLM: una barra de
  // progreso que no mide nada. Ahora no hay fases, hay reloj.
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Narrativa que llega por el stream antes de que exista la respuesta final.
  // NO se commitea al hilo: se muestra en la burbuja de "procesando" y se
  // descarta en cuanto llega el `result` (que la reemplaza) o el intento
  // termina. Es lo que evita que quede media respuesta pegada en el chat si el
  // stream se corta: lo parcial nunca entra en `threads`.
  const [streamingNarrative, setStreamingNarrative] = useState('');

  // Tokens recibidos todavia no volcados al estado. Son refs y no mas estado a
  // proposito: entre un volcado y el siguiente no hay nada que renderizar, y
  // un `setState` por token es justo lo que se esta evitando.
  const streamBufferRef = useRef('');
  const streamFlushTimerRef = useRef<number | null>(null);

  // Unico punto que escribe texto del stream en el estado. Por construccion
  // sigue sin tocar `threads`: la garantia de que lo parcial nunca se commitea no
  // se relajo para ganar rendimiento, solo se agrupo. No se pierde ningun delta
  // porque el buffer solo se vacia cuando su contenido ya esta en el estado, o
  // cuando lo tira `discardStreamingNarrative`.
  const flushStreamBuffer = useCallback(() => {
    if (streamFlushTimerRef.current !== null) {
      clearTimeout(streamFlushTimerRef.current);
      streamFlushTimerRef.current = null;
    }
    const pending = streamBufferRef.current;
    if (!pending) return;
    streamBufferRef.current = '';
    setStreamingNarrative((prev) => prev + pending);
  }, []);

  // Descartar lo parcial, con el mismo criterio de siempre (nunca entra al
  // hilo: lo reemplaza el resultado o se cae el intento), pero ahora hay tambien
  // un buffer que puede quedar pendiente en vuelo y hay que cancelar.
  const discardStreamingNarrative = useCallback(() => {
    if (streamFlushTimerRef.current !== null) {
      clearTimeout(streamFlushTimerRef.current);
      streamFlushTimerRef.current = null;
    }
    streamBufferRef.current = '';
    setStreamingNarrative('');
  }, []);

  // Si el dashboard se desmonta con un volcado pendiente, el timer sigue vivo
  // hasta 80 ms y escribe contra un estado que ya no muestra nadie.
  useEffect(
    () => () => {
      if (streamFlushTimerRef.current !== null) {
        clearTimeout(streamFlushTimerRef.current);
      }
    },
    []
  );

  // El endpoint de stream es una mejora de latencia, no una capacidad. Si el
  // navegador o la red no lo bancan, la consulta va por `sendQuery` y nadie
  // nota la diferencia. Se desactiva sola tras un fallo para no reintentar el
  // stream en cada consulta si el problema es persistente.
  const [streamingEnabled, setStreamingEnabled] = useState(true);

  // El unico setInterval del hook, y vive atado a `isGenerating`: React lo
  // limpia al cambiar el flag o al desmontar, asi que no puede quedar tickeando
  // despues de que la request termino.
  useEffect(() => {
    if (!isGenerating) {
      setElapsedSeconds(0);
      return;
    }
    const startedAt = Date.now();
    setElapsedSeconds(0);
    const ticker = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(ticker);
  }, [isGenerating]);

  // Sync threads from backend on login
  useEffect(() => {
    if (!user) return;
    let isMounted = true;

    const loadBackendThreads = async () => {
      try {
        const remoteSummaries = await queryService.getThreads();
        if (!isMounted) return;
        setThreadsError(null);
        setThreadsLoaded(true);
        if (remoteSummaries.length > 0) {
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
      } catch (err: any) {
        if (!isMounted) return;
        // El cache local sigue en pantalla (es historial de este navegador, no
        // del servidor), pero la UI lo dice: no se presento como confirmado.
        setThreadsError(err.message || 'No se pudo consultar el historial en el servidor.');
      }
    };

    loadBackendThreads();
    return () => {
      isMounted = false;
    };
  }, [user, storageKey]);

  // Check for shared thread URL parameter ?thread=<id>
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const sharedId = params.get('thread');
    if (sharedId) {
      queryService.getSharedThread(sharedId).then((sharedThread) => {
        if (sharedThread) {
          const formatted: FullThread = {
            id: sharedThread.id,
            title: sharedThread.title,
            timestamp: sharedThread.updated_at ? new Date(sharedThread.updated_at).toLocaleDateString() : 'Compartido',
            connection_id: sharedThread.connection_id,
            results: sharedThread.results || [],
          };
          setThreads((prev) => {
            if (prev.some((t) => t.id === sharedThread.id)) {
              return prev.map((t) => (t.id === sharedThread.id ? formatted : t));
            }
            return [formatted, ...prev];
          });
          setActiveThreadId(sharedThread.id);
          notify('info', `Consulta compartida cargada: "${sharedThread.title}"`);
        } else {
          notify('warning', 'El enlace compartido no trae historial: esa conversación no existe o fue eliminada.');
        }
      }).catch(() => {
        notify('error', 'No se pudo consultar la conversación compartida (sin permiso o error de red).');
      });
    }
  }, []);

  // Persist threads to localStorage on change
  // Lo que se escribe es el snapshot recortado (ver PERSISTED_THREADS_LIMIT), no
  // `threads`. Lo que se muestra sigue siendo `threads` completo: el recorte es
  // del disco, no de la pantalla.
  const lastPersistedRef = useRef<{ key: string; payload: string } | null>(null);
  // Un aviso por clave, no uno por cambio de `threads`: sin esto, mientras la
  // cuota siga llena cada consulta nueva vuelve a disparar la misma advertencia.
  const quotaWarnedKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const payload = JSON.stringify(threads.slice(0, PERSISTED_THREADS_LIMIT));
    // Si el serializado no cambio, no se reescribe: el montaje relee lo que
    // acaba de leer del mismo lugar y el sync del backend reordena el mismo
    // historial. El string sirve de comparador porque dos arrays con el mismo
    // contenido dan el mismo JSON.
    if (lastPersistedRef.current?.key === storageKey && lastPersistedRef.current.payload === payload) {
      return;
    }
    try {
      localStorage.setItem(storageKey, payload);
      lastPersistedRef.current = { key: storageKey, payload };
      quotaWarnedKeyRef.current = null;
    } catch (err) {
      // Cualquier otro fallo (navegacion privada que tira SecurityError al
      // escribir) se sigue ignorando como antes; lo unico que se avisa es la
      // cuota agotada, que es el caso donde el historial se pierde en silencio.
      if (!isQuotaError(err) || quotaWarnedKeyRef.current === storageKey) return;
      quotaWarnedKeyRef.current = storageKey;
      notify(
        'warning',
        'Este navegador dejó de guardar el historial: se superó el límite de almacenamiento local (~5 MB). Lo que ves en pantalla y lo que el servidor ya confirmó siguen ahí, pero si recargás esta página se pierde lo que no esté guardado en el servidor.'
      );
    }
  }, [threads, storageKey, notify]);

  // Auto-scroll on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [threads, isGenerating, activeThreadId, pendingPrompt]);

  const activeThread = useMemo(
    () => threads.find((t) => t.id === activeThreadId),
    [threads, activeThreadId]
  );

  // `threads` se muta creando arrays y objetos nuevos (nunca in situ), asi que la
  // referencia es un comparador legitimo: si no cambio `threads`, estos objetos
  // son los mismos de ayer y el memo es correcto.
  const sidebarThreads: ChatThread[] = useMemo(
    () =>
      threads.map((t) => ({
        id: t.id,
        title: t.title,
        timestamp: t.timestamp,
      })),
    [threads]
  );

  const handleSelectThread = useCallback(async (id: string) => {
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
  }, [threads]);

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

  const handleDeleteThread = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const previous = threads;
    setThreads((prev) => prev.filter((t) => t.id !== id));
    if (activeThreadId === id) {
      setActiveThreadId(null);
    }
    try {
      const outcome = await queryService.deleteThread(id);
      notify(
        outcome === 'already_absent' ? 'warning' : 'info',
        outcome === 'already_absent'
          ? 'Esa conversación no estaba en el servidor; solo se quitó de este navegador.'
          : 'Conversación eliminada del historial.'
      );
    } catch (err: any) {
      // El servidor no confirmó nada: se revierte el borrado optimista en vez
      // de mostrar un éxito que un reload deshace.
      setThreads(previous);
      if (activeThreadId === id) {
        setActiveThreadId(id);
      }
      notify('error', err.message || 'No se pudo eliminar la conversación en el servidor; sigue en el historial.');
    }
  }, [threads, activeThreadId, notify]);

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

  const handleEditPrompt = useCallback((question: string) => {
    setPromptInput(question);
    promptTextareaRef.current?.focus();
    notify('info', 'Pregunta cargada en el editor para reintentar.');
  }, [notify]);

  // Deps estables durante todo el stream salvo en los dos flancos (arranque y
  // `finally`): por eso el token no cambia la identidad de este callback ni la
  // del resto de lo que el hook expone.
  const handleSendPrompt = useCallback(async (text: string) => {
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
    setElapsedSeconds(0);
    discardStreamingNarrative();

    const startedAt = Date.now();
    let timedOut = false;

    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current === controller) {
        timedOut = true;
        controller.abort();
        // Que paso y que no se resuelve solo: el motor local sigue vivo, la
        // peticion ya habia salido del navegador y este corte solo abandona la
        // espera. Decir "cancelada" a secas invita a pensar que no se ejecuto
        // nada, y el backend pudo haber generado y ejecutado la consulta igual.
        notify(
          'warning',
          `Se cortó la espera a los ${REQUEST_TIMEOUT_MS / 1000} s. El modelo local no llegó a responder a tiempo: la pregunta ya se había enviado y el servidor pudo seguir trabajándola hasta terminar, pero su resultado se descartó. Podés reintentarla; para consultas más pesadas conviene una pregunta más acotada.`
        );
      }
    }, REQUEST_TIMEOUT_MS);

    try {
      // Primero el stream (lee la narrativa antes de tiempo), con caida al
      // camino que ya funcionaba. Los dos caminos comparten el mismo
      // AbortController y el mismo timeout de arriba, asi que cancelar y el
      // corte por tiempo cortan los dos igual.
      //
      // El fallback reintenta la consulta desde cero: es una segunda llamada al
      // LLM, no una continuacion. Solo ocurre si el stream no produjo un
      // `result` completo.
      let newResult: QueryResult | null = null;

      if (streamingEnabled) {
        try {
          newResult = await queryService.sendQueryStreaming(
            trimmed,
            activeConnectionId || undefined,
            conversationHistory.length > 0 ? conversationHistory : undefined,
            controller.signal,
            (chunk) => {
              // Solo se acumula si este controller sigue siendo el vigente: si
              // el usuario ya cancelo y mando otra consulta, el texto viejo no
              // se escribe en la burbuja de la nueva.
              if (abortControllerRef.current === controller) {
                streamBufferRef.current += chunk;
                // Un volcado cada STREAM_FLUSH_MS mientras siga llegando texto.
                // No se pierde nada: el buffer se acumula y se vuelca entero.
                if (streamFlushTimerRef.current === null) {
                  streamFlushTimerRef.current = window.setTimeout(flushStreamBuffer, STREAM_FLUSH_MS);
                }
              }
            }
          );
        } catch (streamErr: any) {
          // Cancelar y el timeout NO son "el stream no funciono": son decisiones
          // del usuario o el reloj, y ya tienen su propio mensaje. Reintentar
          // aca lanzaria una segunda consulta que el usuario no pidio.
          if (streamErr?.name === 'AbortError' || timedOut) {
            throw streamErr;
          }
          // Cualquier otro fallo del stream es recuperable: se apaga el stream
          // para no insistir y se va por el camino de siempre.
          setStreamingEnabled(false);
        }
      }

      if (!newResult) {
        newResult = await queryService.sendQuery(
          trimmed,
          userRole,
          activeConnectionId || undefined,
          settings,
          controller.signal,
          conversationHistory.length > 0 ? conversationHistory : undefined
        );
      }

      // Llego la verdad: la narrativa parcial se descarta y la muestra el
      // resultado completo, que es el unico que se commitea al hilo.
      discardStreamingNarrative();

      const vStatus = newResult.traceability?.validation_status;
      // El backend emite prefijos: 'APROBADO', 'APROBADO_CONVERSACIONAL',
      // 'APROBADO (Contexto Asistente)' (ver response_builder.py).
      if (vStatus && !vStatus.startsWith('APROBADO')) {
        if (vStatus.includes('RECHAZADO')) {
          notify('warning', `Consulta bloqueada por AST Guardrail (${vStatus}) según perfil ${userRole}.`);
        } else if (vStatus.includes('ERROR')) {
          notify('error', `Error al procesar consulta SQL (${vStatus}).`);
        }
      }

      // Updater puro: el POST va afuera. Dentro del updater es un efecto
      // secundario y React 18 StrictMode lo invoca dos veces en dev -> dos POST.
      let newResults: QueryResult[] = [];
      let threadTitleForSave = threadTitle;
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id !== currentThreadId) return t;
          newResults = [...t.results, newResult];
          threadTitleForSave = t.title;
          return { ...t, results: newResults };
        })
      );

      if (newResults.length > 0) {
        queryService.saveThread({
          id: currentThreadId,
          title: threadTitleForSave,
          connection_id: activeConnectionId || 1,
          results: newResults,
        }).then((saved) => {
          if (!saved) {
            notify('warning', 'La conversación no se pudo guardar en el servidor; queda solo en este navegador.');
          }
        });
      }
    } catch (err: any) {
      // AbortError tiene dos causas y dos mensajes distintos. El timeout ya
      // notificó con su explicación, asi que no se duplica. Si fue el botón de
      // cancelar, se dice qué se canceló y qué no.
      if (err.name === 'AbortError') {
        if (!timedOut) {
          notify(
            'info',
            `Cancelaste la consulta a los ${Math.round((Date.now() - startedAt) / 1000)} s. La espera en este navegador se cortó, pero la petición ya había llegado al servidor y el motor local puede seguir trabajándola hasta terminar. La conversación no cambió.`
          );
        }
        return;
      }
      notify('error', err.message || 'Error al conectar con la base de datos o el motor LLM local.');
    } finally {
      clearTimeout(timeoutId);
      setIsGenerating(false);
      setPendingPrompt(null);
      // La narrativa parcial nunca sobrevive al intento: o la reemplazo el
      // resultado completo, o se cae el stream y se va por `sendQuery`. Lo que
      // se descarto no se guarda en ningun lado (ni el estado ni el buffer).
      discardStreamingNarrative();
    }
  }, [
    activeConnectionId,
    activeThread,
    activeThreadId,
    discardStreamingNarrative,
    flushStreamBuffer,
    isGenerating,
    notify,
    settings,
    streamingEnabled,
    userRole,
  ]);

  // Cancelar la consulta en curso. Aborta de verdad (el signal llega al fetch,
  // ver query_service.executeQuery) y el `finally` de handleSendPrompt devuelve
  // la UI a un estado usable: input habilitado, isGenerating false, pendingPrompt
  // limpio. No se afirma que el trabajo del servidor se deshizo, porque no se
  // deshizo.
  const handleCancelPrompt = useCallback(() => {
    const controller = abortControllerRef.current;
    if (!controller) return;
    abortControllerRef.current = null;
    controller.abort();
    setIsGenerating(false);
    setPendingPrompt(null);
    // Lo que se habia leido del stream no es una respuesta: es texto sin
    // confirmar. Cancelar no lo deja pegado en el chat.
    discardStreamingNarrative();
  }, [discardStreamingNarrative]);

  const handleFeedback = useCallback(async (
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
  }, [activeConnectionId, notify]);

  // El objeto que devuelve el hook es una referencia nueva en cada render, y eso
  // invalida cualquier `React.memo` o comparacion por referencia aguas abajo
  // aunque no haya cambiado nada. Se congela mientras ninguna entrada cambie.
  // No se envuelve el hook en un contexto ni se agrega estado: el hook ya
  // expone todo lo que la pagina necesita, solo falta que las referencias sean
  // estables. `longWaitNotice` se calcula aca para que sea un booleano y no una
  // expresion suelta imposible de comparar.
  const longWaitNotice = elapsedSeconds >= LONG_WAIT_NOTICE_SECONDS;

  return useMemo(() => ({
    user,
    userRole,
    settings,
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
    threads,
    threadsLoaded,
    threadsError,
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
    handleCancelPrompt,
    handleSelectConnection,
    handleEditPrompt,
    handleFeedback,
  }), [
    user,
    userRole,
    settings,
    promptInput,
    isGenerating,
    elapsedSeconds,
    longWaitNotice,
    streamingNarrative,
    activeTraceability,
    isMobileHistoryOpen,
    activeDatabaseName,
    activeConnectionId,
    connectors,
    promptSuggestions,
    threads,
    threadsLoaded,
    threadsError,
    activeThreadId,
    activeThread,
    sidebarThreads,
    pendingPrompt,
    handleSelectThread,
    handleNewThread,
    handleDeleteThread,
    handleSendPrompt,
    handleCancelPrompt,
    handleSelectConnection,
    handleEditPrompt,
    handleFeedback,
  ]);
}

