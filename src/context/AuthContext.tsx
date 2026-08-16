import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AppSettings } from '../types';
import { authService } from '../services/auth_service';

type PageView = 'login' | 'dashboard' | 'settings' | 'admin';

interface AuthContextType {
  user: User | null;
  activePage: PageView;
  settings: AppSettings;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, roleId?: number, isAdmin?: boolean) => Promise<void>;
  loginDemo: (username: string, role?: string, isAdmin?: boolean) => void;
  logout: () => void;
  setActivePage: (page: PageView) => void;
  updateSettings: (newSettings: Partial<AppSettings>) => void;
  clearError: () => void;
}

const defaultSettings: AppSettings = {
  llm_provider: 'llama_cpp',
  ollama_url: 'http://127.0.0.1:8080',
  ollama_model: 'Observerx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M',
  postgres_host: 'localhost',
  postgres_port: 5432,
  postgres_db: 'democratizacion_metadatos',
  auto_detect_llm: true,
};

const loadPersistedSettings = (): AppSettings => {
  try {
    const stored = localStorage.getItem('app_settings');
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) };
    }
  } catch { /* ignore parse errors */ }
  return defaultSettings;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activePage, setActivePage] = useState<PageView>('login');
  const [settings, setSettings] = useState<AppSettings>(loadPersistedSettings);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Restore session from token on app startup
  useEffect(() => {
    const restoreSession = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const profile = await authService.getCurrentUser();
          setUser(profile);
          setActivePage('dashboard');
        } catch {
          authService.logout();
          setUser(null);
          setActivePage('login');
        }
      } else {
        // Require explicit login / registration on page entry
        setUser(null);
        setActivePage('login');
      }
      setIsLoading(false);
    };

    restoreSession();
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await authService.login(username, password);
      setUser(res.user);
      setActivePage('dashboard');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error de inicio de sesión. Revisa usuario y contraseña.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (username: string, email: string, password: string, roleId?: number, isAdmin?: boolean) => {
    setIsLoading(true);
    setError(null);
    try {
      await authService.register({ username, email, password, role_id: roleId, is_admin: isAdmin });
      // Auto login after successful registration
      await login(username, password);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error en el registro. Intenta con otro usuario o correo.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const loginDemo = (username: string, role: string = 'Analista Financiero', isAdmin: boolean = false) => {
    setUser({
      id: Date.now(),
      username,
      email: `${username}@empresa.com`,
      is_admin: isAdmin,
      role_name: role,
    });
    setActivePage('dashboard');
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setActivePage('login');
  };

  const updateSettings = (newSettings: Partial<AppSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      try {
        localStorage.setItem('app_settings', JSON.stringify(updated));
      } catch { /* ignore storage errors */ }
      return updated;
    });
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        activePage,
        settings,
        isLoading,
        error,
        login,
        register,
        loginDemo,
        logout,
        setActivePage,
        updateSettings,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
