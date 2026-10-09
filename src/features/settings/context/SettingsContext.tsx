import React, { createContext, useContext, useState, useCallback, useMemo, useRef } from 'react';
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
  updateSettings: (newSettings: Partial<AppSettings>) => boolean;
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
  const settingsRef = useRef<AppSettings>(settings);
  settingsRef.current = settings;

  // Returns whether the write actually persisted. The previous version wrote
  // localStorage inside the setSettings updater — a render-phase side effect
  // that runs twice under StrictMode — and swallowed quota errors, so the UI
  // reported "guardado correctamente" for a config that was never stored.
  const updateSettings = useCallback((newSettings: Partial<AppSettings>): boolean => {
    const next = { ...settingsRef.current, ...newSettings };
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
    } catch {
      return false;
    }
    settingsRef.current = next;
    setSettings(next);
    return true;
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
