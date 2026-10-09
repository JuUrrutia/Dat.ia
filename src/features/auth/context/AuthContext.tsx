import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { User, AppSettings } from '../../../types';
import { authService } from '../services/auth_service';
import { getAuthToken, PASSWORD_CHANGE_PENDING_EVENT } from '../../../shared/api/api_client';
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

  logout: () => void;
  setActivePage: (page: PageView) => void;
  updateSettings: (newSettings: Partial<AppSettings>) => boolean;
  clearError: () => void;
  /** Limpia `must_change_password` en el estado tras un cambio confirmado. */
  completePasswordChange: () => void;
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
        } catch (err: any) {
          // Un 401 significa que el token expiró o fue revocado: la sesión NO existe.
          // Limpiamos token y usuario cacheado y mandamos a /login.
          // Cualquier otro error (500, red caída) deja el token válido: usamos el
          // usuario cacheado para no expulsar al usuario por un fallo del backend.
          if (err?.response?.status === 401) {
            authService.logout();
            try {
              localStorage.removeItem(USER_KEY);
            } catch { /* ignore */ }
            setUser(null);
            setActivePage('login');
          } else if (savedUser) {
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

  // RETIRADO: `loginDemo` fabricaba una sesion local con is_admin:true y la guardaba
  // en localStorage sin.token. LoginPage lo llamaba cuando el login real fallaba, de
  // modo que un password incorrecto, una cuenta bloqueada o el backend caido
  // entraban igual y el Header mostraba "Super Administrador". Se deja constancia
  // porque el patron (fallar hacia algo que parece correcto) es tentador de
  // reintroducir: si el login falla, el login falla.

  const logout = useCallback(() => {
    authService.logout();
    try {
      // Cache de admin del usuario que sale: los conectores guardan host,
      // database_name y username, y la matriz RBAC la lista de usuarios. Se
      // borran antes de perder el id que los namespacea, o el siguiente usuario
      // de la misma maquina los hereda.
      Object.keys(localStorage)
        .filter((k) => k.startsWith('datia_corporate_connectors') || k.startsWith('datia_governance_users'))
        .forEach((k) => localStorage.removeItem(k));
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

  // El 403 de cambio pendiente puede saltar en cualquier momento (un admin resetea
  // la clave de una sesion ya abierta). El error igual sube al consumidor para que
  // la pantalla lo muestre, pero ademas se abre el formulario: la causa es conocida
  // y accionable, asi que no puede quedar solo como texto de error.
  useEffect(() => {
    const onPending = () => {
      setUser((prev) => (prev ? { ...prev, must_change_password: true } : prev));
    };
    window.addEventListener(PASSWORD_CHANGE_PENDING_EVENT, onPending);
    return () => window.removeEventListener(PASSWORD_CHANGE_PENDING_EVENT, onPending);
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
      logout,
      setActivePage: handleSetActivePage,
      updateSettings,
      clearError,
      completePasswordChange: handlePasswordChangeSuccess,
    }),
    [
      user,
      activePage,
      settings,
      isLoading,
      error,
      login,
      register,
      logout,
      handleSetActivePage,
      updateSettings,
      clearError,
      handlePasswordChangeSuccess,
    ]
  );

  // El modal de cambio forzado ya NO se monta como overlay acá. Con el flag
  // activo el guard de rutas (ProtectedLayout) navega a /change-password, que es
  // la unica pantalla permitida: el dashboard no llega a montarse y por lo tanto
  // no dispara los requests que el backend responde con 403. Montarlo encima
  // dejaba la app entera pidiendo datos que no podia tener.
  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
};
