import axios from 'axios';

const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';
const TOKEN_STORAGE_KEY = 'datia_auth_token:v1';

let inMemoryToken: string | null = (() => {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
})();

export const setAuthToken = (token: string | null) => {
  inMemoryToken = token;
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage quota/security restrictions
  }
};

export const getAuthToken = (): string | null => {
  if (!inMemoryToken) {
    try {
      inMemoryToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      inMemoryToken = null;
    }
  }
  return inMemoryToken;
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 300000,
});

// Interceptor to inject JWT token into all outgoing requests
apiClient.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);
