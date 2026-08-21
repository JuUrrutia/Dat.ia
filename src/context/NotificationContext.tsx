import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { ToastNotification, ToastType } from '../types';

interface NotificationContextType {
  toasts: ToastNotification[];
  notify: (type: ToastType, message: string, options?: { duration?: number }) => void;
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

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

  const contextValue = useMemo(
    () => ({
      toasts,
      notify,
      dismiss,
    }),
    [toasts, notify, dismiss]
  );

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
