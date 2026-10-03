import { useState, useEffect, useRef } from 'react';
import { AppSettings } from '../../../types';
import { llmClientService, LLMConnectionTestResult, LLMCompletionTestResult } from '../../chat/services/llm_service';
import { apiClient } from '../../../shared/api/api_client';
import { DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER } from '../../../constants';

type LLMProvider = AppSettings['llm_provider'];

export function useSettingsDiagnostics(settings: AppSettings, updateSettings: (newSettings: Partial<AppSettings>) => boolean) {
  const [provider, setProvider] = useState<LLMProvider>(settings.llm_provider || (DEFAULT_LLM_PROVIDER as any));
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
  const [saveError, setSaveError] = useState<string | null>(null);

  // Re-entry guard refs
  const isTestingLLMRef = useRef(false);
  const isTestingInferenceRef = useRef(false);
  const isTestingPGRef = useRef(false);

  // Modelos y endpoint que el servidor reporto en la ultima prueba. Son una
  // SUGERENCIA: el boton "Probar" diagnostica, no configura. Antes los aplicaba
  // solo, asi que un diagnostico reescribia url/proveedor/modelo y el siguiente
  // "Guardar" persistia un servidor que el admin nunca eligio.
  const [detectedModels, setDetectedModels] = useState<string[]>([]);
  const [detectedEndpoint, setDetectedEndpoint] = useState<{ url: string; prov: LLMProvider } | null>(null);

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

  // Per-provider memory of the url/model the admin typed. Switching provider
  // used to overwrite both unconditionally, so an admin pointing at
  // http://192.168.1.5:1234 who clicked another provider to test it lost the
  // endpoint and the model with no warning, then saved localhost.
  const perProviderRef = useRef<Record<string, { url: string; model: string }>>({});

  const PROVIDER_DEFAULTS: Record<string, { url: string; model: string }> = {
    llama_cpp: { url: 'http://127.0.0.1:8080', model: 'Qwen3.8-27B' },
    ollama: { url: 'http://localhost:11434', model: 'qwen2.5-coder:7b' },
    openai_compatible: { url: 'http://localhost:1234', model: 'local-model' },
  };

  const handleProviderChange = (newProvider: LLMProvider) => {
    perProviderRef.current[String(provider)] = { url: ollamaUrl, model: modelName };
    setProvider(newProvider);

    const remembered = perProviderRef.current[String(newProvider)];
    if (remembered) {
      setOllamaUrl(remembered.url);
      setModelName(remembered.model);
      return;
    }
    const fallback = PROVIDER_DEFAULTS[String(newProvider)];
    if (fallback) {
      setOllamaUrl(fallback.url);
      setModelName(fallback.model);
    }
  };

  const handleTestLLMConnection = async () => {
    if (isTestingLLMRef.current) return;
    isTestingLLMRef.current = true;
    setTestingLLM(true);
    setLlmTestResult(null);
    setDetectedEndpoint(null);

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
            // Solo lo que el servidor reporto. No se agrega el modelo configurado
            // a mano para "que la lista no se vea vacia".
            setDetectedModels(res.available_models);
            if (ep.url === ollamaUrl) {
              // The configured endpoint answered: a real success.
              setLlmTestResult(res);
              setDetectedEndpoint(null);
            } else {
              // A fallback answered, NOT the configured URL. Reporting success
              // here paints a green banner directly under a dead host, and the
              // admin then saves a broken config.
              setDetectedEndpoint({ url: ep.url, prov: ep.prov });
              setLlmTestResult({
                success: false,
                message: `El endpoint configurado (${ollamaUrl}) no respondió, pero se detectó un servidor LLM activo en ${ep.url}.`,
                available_models: res.available_models,
                latency_ms: res.latency_ms,
              });
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

  const handleApplyDetected = () => {
    if (!detectedEndpoint) return;
    setOllamaUrl(detectedEndpoint.url);
    setProvider(detectedEndpoint.prov);
    setDetectedEndpoint(null);
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
    const persisted = updateSettings({
      llm_provider: provider,
      ollama_url: ollamaUrl,
      ollama_model: modelName,
      postgres_host: pgHost,
      postgres_port: pgPort,
      postgres_db: pgDb,
    });
    if (persisted) {
      setSaveError(null);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } else {
      setSavedSuccess(false);
      setSaveError('No se pudo guardar la configuración: el almacenamiento local rechazó la escritura.');
    }
  };

  return {
    provider,
    setProvider,
    ollamaUrl,
    setOllamaUrl,
    modelName,
    setModelName,
    pgHost,
    setPgHost,
    pgPort,
    setPgPort,
    pgDb,
    setPgDb,
    testingLLM,
    llmTestResult,
    testPrompt,
    setTestPrompt,
    testingInference,
    inferenceResult,
    testingPG,
    pgStatus,
    savedSuccess,
    saveError,
    // The whole page is one <form>. Without this the admin could type a host
    // and model, click the header nav, come back, and find every field reset
    // with no message at all.
    dirty:
      provider !== settings.llm_provider ||
      ollamaUrl !== settings.ollama_url ||
      modelName !== settings.ollama_model ||
      pgHost !== settings.postgres_host ||
      pgPort !== settings.postgres_port ||
      pgDb !== settings.postgres_db,
    detectedModels,
    detectedEndpoint,
    elapsedSeconds,
    handleProviderChange,
    handleTestLLMConnection,
    handleApplyDetected,
    handleRunInferenceTest,
    handleTestPG,
    handleSave,
  };
}
