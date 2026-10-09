/**
 * `127.0.0.1` y NO `localhost`, y la diferencia no es cosmetics.
 *
 * En Windows (y en la mayoría de los setups de desarrollo) `localhost` resuelve
 * primero a `::1` (AAAA) y después a `127.0.0.1` (A). El backend se levanta con
 * `HOST=127.0.0.1` (`backend/app/core/config.py`), o sea SOLO en IPv4.
 *
 * Herramientas de línea de comandos como curl hacen fallback al segundo
 * endereço cuando el primero rechaza la conexión, y por eso `curl
 * http://localhost:8000` siempre funcionó y dio la impresión de que la URL no
 * tenía problema. El `fetch` del navegador NO hace ese fallback: pide `[::1]`,
 * nadie escucha, y la promesa rechaza con `TypeError: Failed to fetch` — sin
 * código HTTP, sin respuesta, sin nada que el backend pueda registrar.
 *
 * Como el backend elige escuchar en el loopback IPv4, la dirección correcta
 * para hablar con él es el loopback IPv4. `localhost` es ambiguo; `127.0.0.1`
 * no lo es.
 *
 * La alternativa sería hacer que el backend escuche en `::` para cubrir ambos,
 * pero eso además de ser un cambio de configuración abriría el puerto a la LAN,
 * que es justo lo que el diseño local-first no quiere. Fijar el cliente es
 * menos invasivo y no cambia la postura de seguridad.
 */
const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string) || 'http://127.0.0.1:8000/api/v1';
const TOKEN_KEY = 'datia_auth_token:v1';
let inMemoryToken: string | null = null;

try {
  inMemoryToken = localStorage.getItem(TOKEN_KEY);
} catch {
  inMemoryToken = null;
}

export const setAuthToken = (token: string | null) => {
  inMemoryToken = token;
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Ignore storage issues
  }
};

export const getAuthToken = (): string | null => {
  if (!inMemoryToken) {
    try {
      inMemoryToken = localStorage.getItem(TOKEN_KEY);
    } catch {
      inMemoryToken = null;
    }
  }
  return inMemoryToken;
};

// `get_current_user` responde 403 con este detalle mientras `must_change_password`
// sigue en True. No es un error de permisos: es una instruccion accionable, y sin
// esto la app la muestra como "error generico" y el usuario no tiene por donde
// cambiar la clave. El evento lo escucha AuthContext y abre el formulario forzado.
export const PASSWORD_CHANGE_PENDING_EVENT = 'datia:password-change-pending';

const isPasswordChangePending = (status: number, data: any): boolean =>
  status === 403 &&
  typeof data?.detail === 'string' &&
  data.detail.includes('/auth/change-password');

interface RequestConfig {
  params?: Record<string, any>;
  headers?: Record<string, string>;
  responseType?: string;
  signal?: AbortSignal;
}

export interface SseEvent {
  event: string;
  data: any;
}

/**
 * Parsea un bloque SSE (`event:` + `data:`) ya recortado.
 *
 * Devuelve `null` para comentarios (`:`) y lineas que no son evento, que es lo
 * que permite ignorar los keep-alives que algunos proxies inyectan.
 */
export const parseSseEvent = (raw: string): SseEvent | null => {
  let event = '';
  const dataLines: string[] = [];

  for (const line of raw.split('\n')) {
    if (line.startsWith(':')) continue;
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!event) return null;
  const payload = dataLines.join('\n');
  try {
    return { event, data: payload ? JSON.parse(payload) : {} };
  } catch {
    return { event, data: {} };
  }
};

async function request<T = any>(path: string, options: RequestInit & RequestConfig = {}): Promise<{ data: T }> {
  let url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
  if (options.params) {
    const searchParams = new URLSearchParams();
    Object.entries(options.params).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      // FastAPI declara `table_names: List[str] = Query(...)`: lee una clave por
      // elemento (`?table_names=a&table_names=b`). `String(['a','b'])` produciría
      // "a,b", que el backend toma como UN solo nombre de tabla y concede acceso a
      // una tabla que no existe en vez de a las dos.
      if (Array.isArray(v)) {
        v.forEach((item) => searchParams.append(k, String(item)));
      } else {
        searchParams.append(k, String(v));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) url += (url.includes('?') ? '&' : '?') + queryString;
  }

  const token = getAuthToken();
  const headers: Record<string, string> = { ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
    delete headers['content-type'];
  } else if (!headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    if (isPasswordChangePending(response.status, errorData)) {
      window.dispatchEvent(new CustomEvent(PASSWORD_CHANGE_PENDING_EVENT));
    }
    const error: any = new Error(errorData.detail || 'API Request Failed');
    error.response = { status: response.status, data: errorData };
    throw error;
  }

  if (options.responseType === 'blob') {
    const blob = await response.blob();
    return { data: blob as unknown as T };
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  return { data };
}

export const apiClient = {
  get: <T = any>(url: string, config?: RequestConfig) =>
    request<T>(url, { method: 'GET', ...config }),

  /**
   * POST que devuelve la `Response` cruda para leer el cuerpo por partes (SSE).
   *
   * `request()` no sirve para esto: hace `await response.text()`, que espera a
   * que el servidor termine de responder, y para un stream eso es exactamente
   * lo que hay que evitar.
   *
   * Reusa el token y el header `Authorization` del resto de la API: el JWT va
   * en la cabecera, nunca en la URL.
   */
  rawStream: async (path: string, body: any, signal?: AbortSignal): Promise<Response> => {
    const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
    const token = getAuthToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      if (isPasswordChangePending(response.status, errorData)) {
        window.dispatchEvent(new CustomEvent(PASSWORD_CHANGE_PENDING_EVENT));
      }
      const error: any = new Error(errorData.detail || 'API Request Failed');
      error.response = { status: response.status, data: errorData };
      throw error;
    }

    return response;
  },
  post: <T = any>(url: string, data?: any, config?: RequestConfig) =>
    request<T>(url, {
      method: 'POST',
      body: data instanceof FormData ? data : data ? JSON.stringify(data) : undefined,
      ...config,
    }),
  put: <T = any>(url: string, data?: any, config?: RequestConfig) =>
    request<T>(url, {
      method: 'PUT',
      body: data instanceof FormData ? data : data ? JSON.stringify(data) : undefined,
      ...config,
    }),
  patch: <T = any>(url: string, data?: any, config?: RequestConfig) =>
    request<T>(url, {
      method: 'PATCH',
      body: data instanceof FormData ? data : data ? JSON.stringify(data) : undefined,
      ...config,
    }),
  delete: <T = any>(url: string, config?: RequestConfig) =>
    request<T>(url, { method: 'DELETE', ...config }),
};
