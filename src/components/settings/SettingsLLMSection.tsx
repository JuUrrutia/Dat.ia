import React from 'react';
import { Cpu, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { AppSettings } from '../../types';
import { LLMConnectionTestResult } from '../../services/llm_service';

type LLMProvider = AppSettings['llm_provider'];

interface SettingsLLMSectionProps {
  provider: LLMProvider;
  ollamaUrl: string;
  modelName: string;
  detectedModels: string[];
  testingLLM: boolean;
  llmTestResult: LLMConnectionTestResult | null;
  onProviderChange: (prov: LLMProvider) => void;
  onOllamaUrlChange: (url: string) => void;
  onModelNameChange: (model: string) => void;
  onTestLLMConnection: () => void;
}

export const SettingsLLMSection: React.FC<SettingsLLMSectionProps> = ({
  provider,
  ollamaUrl,
  modelName,
  detectedModels,
  testingLLM,
  llmTestResult,
  onProviderChange,
  onOllamaUrlChange,
  onModelNameChange,
  onTestLLMConnection,
}) => {
  return (
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
          onClick={onTestLLMConnection}
          disabled={testingLLM}
          className="flex items-center space-x-1.5 text-xs bg-dark-card hover:bg-dark-border text-brand-400 border border-brand-500/30 px-3.5 py-2 rounded-xl transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testingLLM ? 'animate-spin' : ''}`} />
          <span>{testingLLM ? 'Verificando Red...' : 'Auto-detectar / Probar Conexión LLM'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="llm-provider-select" className="block text-xs font-semibold text-gray-300 mb-1.5">Proveedor de Motor LLM</label>
          <select
            id="llm-provider-select"
            value={provider}
            onChange={(e) => onProviderChange(e.target.value as LLMProvider)}
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
          >
            <option value="llama_cpp">llama.cpp / llama.exe serve (http://127.0.0.1:8080)</option>
            <option value="ollama">Ollama Local (http://localhost:11434)</option>
            <option value="openai_compatible">OpenAI-Compatible Local (LM Studio / vLLM)</option>
          </select>
        </div>

        <div>
          <label htmlFor="ollama-url-input" className="block text-xs font-semibold text-gray-300 mb-1.5">URL Servidor Local</label>
          <input
            id="ollama-url-input"
            type="text"
            value={ollamaUrl}
            onChange={(e) => onOllamaUrlChange(e.target.value)}
            placeholder="http://127.0.0.1:8080"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
          />
        </div>

        <div className="md:col-span-2">
          <label htmlFor="model-name-input" className="block text-xs font-semibold text-gray-300 mb-1.5">Nombre del Modelo LLM</label>
          <input
            id="model-name-input"
            type="text"
            value={modelName}
            onChange={(e) => onModelNameChange(e.target.value)}
            placeholder="Qwen3.8-27B"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
          />

          {detectedModels.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-gray-400">Modelos Detectados:</span>
              {detectedModels.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => onModelNameChange(m)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded transition-colors ${
                    modelName === m
                      ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                      : 'bg-dark-base text-gray-400 hover:text-white border border-dark-border'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {llmTestResult && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
            llmTestResult.success
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
          }`}
        >
          {llmTestResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{llmTestResult.message} ({llmTestResult.latency_ms} ms)</span>
        </div>
      )}
    </div>
  );
};
