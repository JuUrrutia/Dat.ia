import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '../services/api_client';
import { SystemHealthResponse } from '../types';
import { useNotifications } from '../context/NotificationContext';

export const DEFAULT_POLLING_INTERVAL_MS = 60000;

export const useSystemHealth = (pollingIntervalMs: number = DEFAULT_POLLING_INTERVAL_MS) => {
  const [healthData, setHealthData] = useState<SystemHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const prevStatusRef = useRef<'OPERATIVO' | 'DEGRADADO' | 'CRITICO' | null>(null);
  const { notify } = useNotifications();

  const fetchHealth = useCallback(async () => {
    try {
      const res = await apiClient.get<SystemHealthResponse>('/system/health');
      const data = res.data;
      setHealthData(data);
      setLastChecked(new Date());

      // State transition notification triggers
      const currentStatus = data.status;
      const prevStatus = prevStatusRef.current;

      if (prevStatus !== null && prevStatus !== currentStatus) {
        if (currentStatus === 'CRITICO') {
          notify(
            'error',
            'Alerta Crítica: El motor LLM local no responde. Verifica que Ollama o llama.cpp esté activo.'
          );
        } else if (currentStatus === 'DEGRADADO' && prevStatus === 'OPERATIVO') {
          notify(
            'warning',
            'Atención: Una o más bases de datos corporativas no responden. El sistema opera en modo degradado.'
          );
        } else if (currentStatus === 'OPERATIVO' && (prevStatus === 'CRITICO' || prevStatus === 'DEGRADADO')) {
          notify(
            'success',
            'Sistema restablecido: El motor LLM y todas las fuentes corporativas están 100% operativas.'
          );
        }
      }

      prevStatusRef.current = currentStatus;
    } catch {
      // Backend offline
      const fallbackStatus = 'CRITICO';
      if (prevStatusRef.current !== fallbackStatus && prevStatusRef.current !== null) {
        notify('error', 'No se pudo contactar al servidor Backend de Datia.');
      }
      prevStatusRef.current = fallbackStatus;
    } finally {
      setIsLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchHealth();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchHealth();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    const intervalId = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchHealth();
      }
    }, pollingIntervalMs);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(intervalId);
    };
  }, [fetchHealth, pollingIntervalMs]);

  return {
    status: healthData?.status || 'OPERATIVO',
    details: healthData,
    lastChecked,
    isLoading,
    refetch: fetchHealth,
  };
};
