import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '../services/api_client';
import { SystemHealthResponse } from '../types';
import { useNotifications } from '../context/NotificationContext';
import { useAuth } from '../context/AuthContext';

export const DEFAULT_POLLING_INTERVAL_MS = 60000;

export const useSystemHealth = (pollingIntervalMs: number = DEFAULT_POLLING_INTERVAL_MS) => {
  const [healthData, setHealthData] = useState<SystemHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const prevStatusRef = useRef<'OPERATIVO' | 'DEGRADADO' | 'CRITICO' | null>(null);
  const { notify } = useNotifications();
  const { settings } = useAuth();

  const fetchHealth = useCallback(async () => {
    try {
      const res = await apiClient.get<SystemHealthResponse>('/system/health', {
        params: {
          base_url: settings?.ollama_url,
          provider: settings?.llm_provider,
          model_name: settings?.ollama_model,
        },
      });
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
            'Alerta Crítica: El motor LLM local no responde. Verifica que llama.exe serve u Ollama esté activo.'
          );
        } else if (currentStatus === 'DEGRADADO' && prevStatus === 'OPERATIVO') {
          notify(
            'warning',
            'Atención: Una o más fuentes de datos corporativas no responden. El sistema opera en modo degradado.'
          );
        } else if (currentStatus === 'OPERATIVO' && (prevStatus === 'CRITICO' || prevStatus === 'DEGRADADO')) {
          notify(
            'success',
            'Sistema 100% Operativo: Motor LLM local y fuentes corporativas conectadas.'
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
  }, [notify, settings?.ollama_url, settings?.llm_provider, settings?.ollama_model]);

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
