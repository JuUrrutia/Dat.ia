import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { User, AppSettings } from '../types';
import { authService } from '../services/auth_service';
import { getAuthToken } from '../services/api_client';
import { MandatoryPasswordChangeModal } from '../components/auth/MandatoryPasswordChangeModal';
import {
  DEFAULT_LLM_PROVIDER,
  DEFAULT_OLLAMA_URL,
  DEFAULT_LLM_MODEL,
  DEFAULT_POSTGRES_HOST,
  DEFAULT_POSTGRES_PORT,
  DEFAULT_POSTGRES_DB
} from '../constants';

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
  llm_provider: DEFAULT_LLM_PROVIDER as any,
  ollama_url: DEFAULT_OLLAMA_URL,
  ollama_model: DEFAULT_LLM_MODEL,
  postgres_host: DEFAULT_POSTGRES_HOST,
  postgres_port: DEFAULT_POSTGRES_PORT,
  postgres_db: DEFAULT_POSTGRES_DB,
  auto_detect_llm: true,
};

const SETTINGS_KEY = 'app_settings:v1';

const loadPersistedSettings = (): AppSettings => {
  try {
    const saved = localStorage.getItem(SETTINGS_KEY);
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  } catch {
    return defaultSettings;
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activePage, setActivePage] = useState<PageView>('login');
  const [settings, setSettings] = useState<AppSettings>(loadPersistedSettings);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Restore session from active in-memory token on app startup
  useEffect(() => {
    const restoreSession = async () => {
      const token = getAuthToken();
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

  const login = useCallback(async (username: string, password: string) => {
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
  }, []);

  const register = useCallback(async (username: string, email: string, password: string, roleId?: number, isAdmin?: boolean) => {
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
  }, [login]);

  const loginDemo = useCallback((username: string, role: string = 'Analista Financiero', isAdmin: boolean = false) => {
    setUser({
      id: Date.now(),
      username,
      email: `${username}@empresa.com`,
      is_admin: isAdmin,
      role_name: role,
    });
    setActivePage('dashboard');
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setActivePage('login');
  }, []);

  const updateSettings = useCallback((newSettings: Partial<AppSettings>) => {
    const updated = { ...settings, ...newSettings };
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
    } catch { /* ignore storage errors */ }
    setSettings(updated);
  }, [settings]);

  const clearError = useCallback(() => setError(null), []);

  const handlePasswordChangeSuccess = useCallback(() => {
    setUser((prev) => (prev ? { ...prev, must_change_password: false } : null));
  }, []);

  const contextValue = useMemo(
    () => ({
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
    }),
    [
      user,
      activePage,
      settings,
      isLoading,
      error,
      login,
      register,
      loginDemo,
      logout,
      updateSettings,
      clearError,
    ]
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      {user && user.must_change_password && (
        <MandatoryPasswordChangeModal
          isOpen={true}
          onSuccess={handlePasswordChangeSuccess}
        />
      )}
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
