import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { AppSettings } from '../../../types';
import {
  DEFAULT_LLM_PROVIDER,
  DEFAULT_OLLAMA_URL,
  DEFAULT_LLM_MODEL,
  DEFAULT_POSTGRES_HOST,
  DEFAULT_POSTGRES_PORT,
  DEFAULT_POSTGRES_DB,
} from '../../../constants';

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (newSettings: Partial<AppSettings>) => void;
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

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<AppSettings>(loadPersistedSettings);

  const updateSettings = useCallback((newSettings: Partial<AppSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
      } catch {
        // Ignore quota errors
      }
      return updated;
    });
  }, []);

  const value = useMemo(
    () => ({
      settings,
      updateSettings,
    }),
    [settings, updateSettings]
  );

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings debe usarse dentro de un SettingsProvider');
  }
  return context;
};

export const useAppSettings = useSettings;
