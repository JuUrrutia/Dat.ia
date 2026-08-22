import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { AppSettings } from '../types';
import { llmClientService, LLMConnectionTestResult, LLMCompletionTestResult } from '../services/llm_service';
import { apiClient } from '../services/api_client';
import { DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER } from '../constants';
import { Settings, CheckCircle2, Save } from 'lucide-react';
import { SettingsLLMSection } from '../components/settings/SettingsLLMSection';
import { SettingsInferenceSection } from '../components/settings/SettingsInferenceSection';
import { SettingsPostgresSection } from '../components/settings/SettingsPostgresSection';

type LLMProvider = AppSettings['llm_provider'];

export const SettingsPage: React.FC = () => {
  const { settings, updateSettings } = useAuth();
  const [provider, setProvider] = useState<LLMProvider>(settings.llm_provider || DEFAULT_LLM_PROVIDER as any);
  const [ollamaUrl, setOllamaUrl] = useState(settings.ollama_url || DEFAULT_OLLAMA_URL);
  const [modelName, setModelName] = useState(settings.ollama_model || DEFAULT_LLM_MODEL);

  const [pgHost, setPgHost] = useState(settings.postgres_host);
  const [pgPort, setPgPort] = useState(settings.postgres_port);
  const [pgDb, setPgDb] = useState(settings.postgres_db);

  // LLM Connectivity Test State
  const [testingLLM, setTestingLLM] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<LLMConnectionTestResult | null>(null);

  // LLM Real Inference Test State
  const [testPrompt, setTestPrompt] = useState('Genera una consulta SQL para obtener el total de ventas e ingresos por categoría en orden descendente');
  const [testingInference, setTestingInference] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<LLMCompletionTestResult | null>(null);

  // PostgreSQL Connection Test State
  const [testingPG, setTestingPG] = useState(false);
  const [pgStatus, setPgStatus] = useState<{ success: boolean; message: string } | null>(null);

  const [savedSuccess, setSavedSuccess] = useState(false);

  // Re-entry guard refs
  const isTestingLLMRef = useRef(false);
  const isTestingInferenceRef = useRef(false);
  const isTestingPGRef = useRef(false);

  // Detected models from auto-detect
  const [detectedModels, setDetectedModels] = useState<string[]>([]);

  // Live timer for inference
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let interval: any;
    if (testingInference) {
      setElapsedSeconds(0);
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(interval);
  }, [testingInference]);

  const handleProviderChange = (newProvider: LLMProvider) => {
    setProvider(newProvider);
    if (newProvider === 'llama_cpp') {
      setOllamaUrl('http://127.0.0.1:8080');
      setModelName('Qwen3.8-27B');
    } else if (newProvider === 'ollama') {
      setOllamaUrl('http://localhost:11434');
      setModelName('qwen2.5-coder:7b');
    } else if (newProvider === 'openai_compatible') {
      setOllamaUrl('http://localhost:1234');
      setModelName('local-model');
    }
  };

  const handleTestLLMConnection = async () => {
    if (isTestingLLMRef.current) return;
    isTestingLLMRef.current = true;
    setTestingLLM(true);
    setLlmTestResult(null);

    try {
      const endpointsToTry: { url: string; prov: LLMProvider }[] = [
        { url: ollamaUrl, prov: provider },
      ];

      if (ollamaUrl !== 'http://127.0.0.1:8080') {
        endpointsToTry.push({ url: 'http://127.0.0.1:8080', prov: 'llama_cpp' });
      }
      if (ollamaUrl !== 'http://localhost:11434') {
        endpointsToTry.push({ url: 'http://localhost:11434', prov: 'ollama' });
      }
      if (ollamaUrl !== 'http://localhost:1234') {
        endpointsToTry.push({ url: 'http://localhost:1234', prov: 'openai_compatible' });
      }

      for (const ep of endpointsToTry) {
        try {
          const res = await llmClientService.testConnection(ep.prov, ep.url, modelName);
          if (res.success) {
            setLlmTestResult(res);
            setDetectedModels(res.available_models);
            if (ep.url !== ollamaUrl) {
              setOllamaUrl(ep.url);
              setProvider(ep.prov);
            }
            if (res.available_models.length > 0 && !res.available_models.includes(modelName)) {
              setModelName(res.available_models[0]);
            }
            return;
          }
        } catch {
          // continue to next endpoint
        }
      }

      setLlmTestResult({
        success: false,
        message: `No se detectó ningún servidor LLM local activo. Verifica que llama.exe serve, Ollama, o LM Studio esté corriendo.`,
        available_models: [],
        latency_ms: 0
      });
    } finally {
      isTestingLLMRef.current = false;
      setTestingLLM(false);
    }
  };

  const handleRunInferenceTest = async () => {
    if (isTestingInferenceRef.current || !testPrompt.trim()) return;
    isTestingInferenceRef.current = true;
    setTestingInference(true);
    setInferenceResult(null);

    try {
      const res = await llmClientService.testCompletion(testPrompt, provider, ollamaUrl, modelName);
      setInferenceResult(res);
    } catch (err: any) {
      setInferenceResult({
        success: false,
        completion_text: '',
        latency_ms: 0,
        message: `Error al probar inferencia: ${err.message}`
      });
    } finally {
      isTestingInferenceRef.current = false;
      setTestingInference(false);
    }
  };

  const handleTestPG = async () => {
    if (isTestingPGRef.current) return;
    isTestingPGRef.current = true;
    setTestingPG(true);
    setPgStatus(null);
    try {
      const res = await apiClient.post<{ success: boolean; message: string }>('/connectors/test-metadata-db', {
        server: pgHost,
        port: Number(pgPort),
        db_name: pgDb,
      });
      setPgStatus({
        success: res.data.success,
        message: res.data.message
      });
    } catch (err: any) {
      setPgStatus({
        success: false,
        message: err.response?.data?.detail || `No se pudo conectar al servidor PostgreSQL en ${pgHost}:${pgPort}.`
      });
    } finally {
      isTestingPGRef.current = false;
      setTestingPG(false);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateSettings({
      llm_provider: provider as any,
      ollama_url: ollamaUrl,
      ollama_model: modelName,
      postgres_host: pgHost,
      postgres_port: Number(pgPort),
      postgres_db: pgDb,
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="w-full h-full flex-1 bg-dark-base overflow-y-auto p-6 space-y-6 custom-scrollbar pb-28">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-brand-400" /> Opciones y Configuración del Sistema
          </h1>
          <p className="text-xs text-gray-400">
            Ajustes del motor de Inteligencia Artificial Local (llama.cpp / Ollama / LM Studio) y base de metadatos
          </p>
        </div>

        {savedSuccess && (
          <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg animate-fadeIn">
            <CheckCircle2 className="w-4 h-4" />
            <span>Configuración guardada exitosamente</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6 max-w-4xl">
        {/* Section 1: Local LLM Configuration */}
        <SettingsLLMSection
          provider={provider}
          ollamaUrl={ollamaUrl}
          modelName={modelName}
          detectedModels={detectedModels}
          testingLLM={testingLLM}
          llmTestResult={llmTestResult}
          onProviderChange={handleProviderChange}
          onOllamaUrlChange={setOllamaUrl}
          onModelNameChange={setModelName}
          onTestLLMConnection={handleTestLLMConnection}
        />

        {/* Section 2: LLM Inference Test */}
        <SettingsInferenceSection
          testPrompt={testPrompt}
          testingInference={testingInference}
          elapsedSeconds={elapsedSeconds}
          inferenceResult={inferenceResult}
          onTestPromptChange={setTestPrompt}
          onRunInferenceTest={handleRunInferenceTest}
        />

        {/* Section 3: PostgreSQL Metadata DB */}
        <SettingsPostgresSection
          pgHost={pgHost}
          pgPort={pgPort}
          pgDb={pgDb}
          testingPG={testingPG}
          pgStatus={pgStatus}
          onPgHostChange={setPgHost}
          onPgPortChange={setPgPort}
          onPgDbChange={setPgDb}
          onTestPG={handleTestPG}
        />

        {/* Action Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="flex items-center space-x-2 text-xs bg-brand-600 hover:bg-brand-500 text-white font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-brand-600/30 transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Guardar Configuración</span>
          </button>
        </div>
      </form>
    </div>
  );
};
