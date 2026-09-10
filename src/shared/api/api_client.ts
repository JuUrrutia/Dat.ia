const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';
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

interface RequestConfig {
  params?: Record<string, any>;
  headers?: Record<string, string>;
  responseType?: string;
}

async function request<T = any>(path: string, options: RequestInit & RequestConfig = {}): Promise<{ data: T }> {
  let url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
  if (options.params) {
    const searchParams = new URLSearchParams();
    Object.entries(options.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) searchParams.append(k, String(v));
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
  delete: <T = any>(url: string, config?: RequestConfig) =>
    request<T>(url, { method: 'DELETE', ...config }),
};
