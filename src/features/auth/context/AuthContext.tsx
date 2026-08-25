import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { User, AppSettings } from '../../../types';
import { authService } from '../services/auth_service';
import { getAuthToken } from '../../../shared/api/api_client';
import { MandatoryPasswordChangeModal } from '../../../components/auth/MandatoryPasswordChangeModal';
import { useSettings } from '../../settings/context/SettingsContext';

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

const USER_KEY = 'datia_auth_user:v1';
const PAGE_KEY = 'datia_active_page:v1';

const loadPersistedUser = (): User | null => {
  try {
    const saved = localStorage.getItem(USER_KEY);
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
};

const loadPersistedPage = (): PageView => {
  try {
    const saved = localStorage.getItem(PAGE_KEY) as PageView;
    if (saved && ['login', 'dashboard', 'settings', 'admin'].includes(saved)) {
      return saved;
    }
    return 'dashboard';
  } catch {
    return 'dashboard';
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { settings, updateSettings } = useSettings();
  const [user, setUser] = useState<User | null>(loadPersistedUser);
  const [activePage, setActivePage] = useState<PageView>(() => {
    const savedUser = loadPersistedUser();
    if (!savedUser && !getAuthToken()) {
      return 'login';
    }
    const page = loadPersistedPage();
    return page === 'login' ? 'dashboard' : page;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const restoreSession = async () => {
      const token = getAuthToken();
      const savedUser = loadPersistedUser();
      const savedPage = loadPersistedPage();

      if (token) {
        try {
          const profile = await authService.getCurrentUser();
          setUser(profile);
          try {
            localStorage.setItem(USER_KEY, JSON.stringify(profile));
          } catch { /* ignore */ }
          setActivePage(savedPage === 'login' ? 'dashboard' : savedPage);
        } catch {
          if (savedUser) {
            setUser(savedUser);
            setActivePage(savedPage === 'login' ? 'dashboard' : savedPage);
          } else {
            authService.logout();
            setUser(null);
            setActivePage('login');
          }
        }
      } else if (savedUser) {
        setUser(savedUser);
        setActivePage(savedPage === 'login' ? 'dashboard' : savedPage);
      } else {
        setUser(null);
        setActivePage('login');
      }
      setIsLoading(false);
    };

    restoreSession();
  }, []);

  const handleSetActivePage = useCallback((page: PageView) => {
    try {
      localStorage.setItem(PAGE_KEY, page);
    } catch { /* ignore */ }
    setActivePage(page);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await authService.login(username, password);
      setUser(res.user);
      try {
        localStorage.setItem(USER_KEY, JSON.stringify(res.user));
        localStorage.setItem(PAGE_KEY, 'dashboard');
      } catch { /* ignore */ }
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
      await login(username, password);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error en el registro. Intenta con otro usuario o correo.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [login]);

  const loginDemo = useCallback((username: string, role: string = 'Analista Financiero & Comercial', isAdmin: boolean = false) => {
    const demoUser: User = {
      id: Date.now(),
      username,
      email: `${username.toLowerCase().replace(/\s+/g, '')}@empresa.com`,
      is_admin: isAdmin,
      role_name: role,
    };
    setUser(demoUser);
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
      localStorage.setItem(PAGE_KEY, 'dashboard');
    } catch { /* ignore */ }
    setActivePage('dashboard');
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    try {
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(PAGE_KEY);
    } catch { /* ignore */ }
    setUser(null);
    setActivePage('login');
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const handlePasswordChangeSuccess = useCallback(() => {
    setUser((prev) => (prev ? { ...prev, must_change_password: false } : null));
    try {
      const saved = loadPersistedUser();
      if (saved) {
        localStorage.setItem(USER_KEY, JSON.stringify({ ...saved, must_change_password: false }));
      }
    } catch { /* ignore storage errors */ }
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
      setActivePage: handleSetActivePage,
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
      handleSetActivePage,
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
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
};
