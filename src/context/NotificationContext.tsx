import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { ToastNotification, ToastType } from '../types';

// Dos contextos, no uno. `toasts` cambia en cada notificacion y con eso
// invalidaba el valor del contexto para TODOS sus consumidores — incluido
// `useChatEngine`, o sea la pagina de chat entera se re-renderizaba por cada
// toast. Ahora solo `ToastContainer` consume la lista; el resto pide `notify`,
// cuya referencia no cambia nunca.

interface NotificationContextType {
  notify: (type: ToastType, message: string, options?: { duration?: number }) => void;
}

interface ToastListContextType {
  toasts: ToastNotification[];
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);
const ToastListContext = createContext<ToastListContextType | undefined>(undefined);

const DEFAULT_DURATION_MS = 5000;

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (type: ToastType, message: string, options?: { duration?: number }) => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const duration = options?.duration ?? DEFAULT_DURATION_MS;

      const newToast: ToastNotification = {
        id,
        type,
        message,
        duration,
      };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  // Sin `toasts` en las deps a proposito: este valor no cambia nunca, que es
  // justo lo que evita el render en cascada.
  const notifyValue = useMemo(() => ({ notify }), [notify]);
  const toastListValue = useMemo(() => ({ toasts, dismiss }), [toasts, dismiss]);

  return (
    <NotificationContext.Provider value={notifyValue}>
      <ToastListContext.Provider value={toastListValue}>
        {children}
      </ToastListContext.Provider>
    </NotificationContext.Provider>
  );
};

/** Para emitir notificaciones. No re-renderiza con la lista de toasts. */
export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

/** Para LEER la lista de toasts. Solo `ToastContainer` debe usar esto. */
export const useToastList = (): ToastListContextType => {
  const context = useContext(ToastListContext);
  if (!context) {
    throw new Error('useToastList must be used within a NotificationProvider');
  }
  return context;
};