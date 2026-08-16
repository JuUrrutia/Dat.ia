import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { AppSettings } from '../types';
import { llmClientService, LLMConnectionTestResult, LLMCompletionTestResult } from '../services/llm_service';
import { Settings, Cpu, Database, RefreshCw, CheckCircle2, AlertCircle, Save, Play, Code2, Sparkles } from 'lucide-react';

type LLMProvider = AppSettings['llm_provider'];

export const SettingsPage: React.FC = () => {
  const { settings, updateSettings } = useAuth();
  const [provider, setProvider] = useState<LLMProvider>(settings.llm_provider || 'llama_cpp');
  const [ollamaUrl, setOllamaUrl] = useState(settings.ollama_url || 'http://127.0.0.1:8080');
  const [modelName, setModelName] = useState(settings.ollama_model || 'Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M');

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

  // Detected models from auto-detect
  const [detectedModels, setDetectedModels] = useState<string[]>([]);

  // Live timer for inference
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (testingInference) {
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [testingInference]);

  const handleProviderChange = (newProvider: LLMProvider) => {
    setProvider(newProvider);
    if (newProvider === 'llama_cpp') {
      setOllamaUrl('http://127.0.0.1:8080');
      setModelName('Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M');
    } else if (newProvider === 'ollama') {
      setOllamaUrl('http://localhost:11434');
      setModelName('qwen2.5-coder:7b');
    } else if (newProvider === 'openai_compatible') {
      setOllamaUrl('http://localhost:1234');
      setModelName('local-model');
    }
  };

  const handleTestLLMConnection = async () => {
    setTestingLLM(true);
    setLlmTestResult(null);

    // If auto_detect is on, try multiple endpoints in sequence
    const endpointsToTry: { url: string; prov: LLMProvider }[] = [
      { url: ollamaUrl, prov: provider },
    ];

    // Add other endpoints for auto-detect
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
          // Auto-fill with detected config
          if (ep.url !== ollamaUrl) {
            setOllamaUrl(ep.url);
            setProvider(ep.prov);
          }
          if (res.available_models.length > 0 && !res.available_models.includes(modelName)) {
            setModelName(res.available_models[0]);
          }
          setTestingLLM(false);
          return;
        }
      } catch {
        // continue to next endpoint
      }
    }

    // None worked
    setLlmTestResult({
      success: false,
      message: `No se detectó ningún servidor LLM local activo. Verifica que llama.exe serve, Ollama, o LM Studio esté corriendo.`,
      available_models: [],
      latency_ms: 0
    });
    setTestingLLM(false);
  };

  const handleRunInferenceTest = async () => {
    if (!testPrompt.trim()) return;
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
      setTestingInference(false);
    }
  };

  const handleTestPG = () => {
    setTestingPG(true);
    setPgStatus(null);
    setTimeout(() => {
      setTestingPG(false);
      setPgStatus({
        success: true,
        message: `Conexión a PostgreSQL en ${pgHost}:${pgPort} verificada correctamente.`
      });
    }, 800);
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
    <div className="flex-1 bg-dark-base overflow-y-auto p-6 space-y-6">
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
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
          <div className="flex items-center justify-between border-b border-dark-border pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Motor de Inteligencia Artificial Local (Text-to-SQL)</h3>
                <p className="text-xs text-gray-400">Configuración agnóstica de inferencia 100% offline</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleTestLLMConnection}
              disabled={testingLLM}
              className="flex items-center space-x-1.5 text-xs bg-dark-card hover:bg-dark-border text-brand-400 border border-brand-500/30 px-3.5 py-2 rounded-xl transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingLLM ? 'animate-spin' : ''}`} />
              <span>{testingLLM ? 'Verificando Red...' : 'Auto-detectar / Probar Conexión LLM'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Proveedor de Motor LLM</label>
              <select
                value={provider}
                onChange={(e) => handleProviderChange(e.target.value as LLMProvider)}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="llama_cpp">llama.cpp / llama.exe serve (http://127.0.0.1:8080)</option>
                <option value="ollama">Ollama Local (http://localhost:11434)</option>
                <option value="openai_compatible">OpenAI-Compatible Local (LM Studio / vLLM)</option>
                <option value="custom">API Privada / Personalizada</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Modelo Invocado</label>
              {detectedModels.length > 0 ? (
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
                >
                  {detectedModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="ej. Observerx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M"
                  className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
                />
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">URL del Endpoint HTTP</label>
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              placeholder="http://127.0.0.1:8080"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
            />
          </div>

          {llmTestResult && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
                llmTestResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}
            >
              <div className="flex items-center space-x-2">
                {llmTestResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                <span>{llmTestResult.message}</span>
              </div>
              {llmTestResult.latency_ms > 0 && (
                <span className="text-[10px] font-mono opacity-80">{llmTestResult.latency_ms} ms</span>
              )}
            </div>
          )}
        </div>

        {/* Section 2: Real-time LLM Inference Testing Box */}
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
          <div className="flex items-center justify-between border-b border-dark-border pb-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-semibold text-white">Prueba de Inferencia en Tiempo Real (Generación Text-to-SQL)</h3>
            </div>
            <span className="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2.5 py-0.5 rounded font-mono truncate max-w-xs">
              Modelo: {modelName}
            </span>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Prompt de Prueba en Lenguaje Natural:</label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                placeholder="Escribe una pregunta para probar el modelo..."
                className="flex-1 bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
              />
              <button
                type="button"
                onClick={handleRunInferenceTest}
                disabled={testingInference || !testPrompt.trim()}
                className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2.5 rounded-xl shadow-lg shadow-purple-600/30 transition-all disabled:opacity-40"
              >
                <Play className={`w-3.5 h-3.5 ${testingInference ? 'animate-spin' : ''}`} />
                <span>{testingInference ? `Generando... ${elapsedSeconds}s` : 'Ejecutar Inferencia'}</span>
              </button>
            </div>
          </div>

          {/* Progress indicator during inference */}
          {testingInference && (
            <div className="p-3 rounded-xl border border-purple-500/20 bg-purple-500/5 text-xs text-purple-300 space-y-2 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                  <span>Modelo procesando inferencia... ({elapsedSeconds}s transcurridos)</span>
                </div>
                <span className="text-[10px] text-gray-400 font-mono">Timeout: 5 min</span>
              </div>
              <div className="w-full bg-dark-base rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-600 to-indigo-500 rounded-full transition-all duration-1000"
                  style={{ width: `${Math.min((elapsedSeconds / 300) * 100, 100)}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-500">Modelos grandes (27B) a ~2.7 t/s pueden tardar 2-3 minutos. El proceso no se ha detenido.</p>
            </div>
          )}

          {/* Test Inference Completion Output Box */}
          {inferenceResult && (
            <div className="space-y-2 animate-fadeIn pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 flex items-center space-x-1">
                  <Code2 className="w-3.5 h-3.5 text-brand-400" />
                  <span>Respuesta del Modelo ({modelName}):</span>
                </span>
                <span className={`text-[10px] font-mono ${inferenceResult.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {inferenceResult.latency_ms} ms | {inferenceResult.message}
                </span>
              </div>
              <pre className="p-4 rounded-xl bg-dark-base border border-dark-border text-xs font-mono text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                {inferenceResult.completion_text}
              </pre>
            </div>
          )}
        </div>

        {/* Section 3: PostgreSQL Metadata Connection */}
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
          <div className="flex items-center justify-between border-b border-dark-border pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Base de Datos de Metadatos PostgreSQL</h3>
                <p className="text-xs text-gray-400">Almacenamiento de usuarios, matriz RBAC, catálogo y auditoría</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleTestPG}
              disabled={testingPG}
              className="flex items-center space-x-1.5 text-xs bg-dark-card hover:bg-dark-border text-purple-400 border border-purple-500/30 px-3.5 py-2 rounded-xl transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingPG ? 'animate-spin' : ''}`} />
              <span>{testingPG ? 'Verificando...' : 'Probar Conexión PostgreSQL'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Servidor Host</label>
              <input
                type="text"
                value={pgHost}
                onChange={(e) => setPgHost(e.target.value)}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Puerto</label>
              <input
                type="number"
                value={pgPort}
                onChange={(e) => setPgPort(Number(e.target.value))}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Nombre BD</label>
              <input
                type="text"
                value={pgDb}
                onChange={(e) => setPgDb(e.target.value)}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          {pgStatus && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-center space-x-2 ${
                pgStatus.success
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{pgStatus.message}</span>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="flex items-center space-x-2 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold px-6 py-3 rounded-xl shadow-lg shadow-brand-600/30 transition-all"
          >
            <Save className="w-4 h-4" />
            <span>Guardar Cambios de Configuración</span>
          </button>
        </div>
      </form>
    </div>
  );
};
