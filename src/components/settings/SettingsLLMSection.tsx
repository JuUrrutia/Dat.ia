import React from 'react';
import { Cpu, RefreshCw, CheckCircle2, AlertCircle, Radio } from 'lucide-react';
import { AppSettings } from '../../types';
import { LLMConnectionTestResult } from '../../features/chat/services/llm_service';

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
    <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4 shadow-xl font-sans">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dark-border/80 pb-3.5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-brand-600/20 to-indigo-600/20 text-brand-400 border border-brand-500/30 shadow-md">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span>Motor IA Local (Text-to-SQL)</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/30">
                100% Offline
              </span>
            </h3>
            <p className="text-[11px] text-gray-400">Inferencia agnóstica sin exfiltración de datos a la nube</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onTestLLMConnection}
          disabled={testingLLM}
          className="flex items-center justify-center space-x-1.5 text-xs font-semibold bg-dark-base/80 hover:bg-dark-card text-brand-300 border border-brand-500/30 hover:border-brand-500/60 px-3.5 py-2 rounded-xl transition-all shadow-sm focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${testingLLM ? 'animate-spin' : ''}`} />
          <span>{testingLLM ? 'Comprobando...' : 'Auto-detectar / Probar LLM'}</span>
        </button>
      </div>

      {/* Inputs Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div>
          <label htmlFor="llm-provider-select" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            Proveedor de Motor LLM
          </label>
          <div className="relative">
            <select
              id="llm-provider-select"
              value={provider}
              onChange={(e) => onProviderChange(e.target.value as LLMProvider)}
              className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors shadow-inner"
            >
              <option value="llama_cpp">llama.cpp / llama.exe serve (http://127.0.0.1:8080)</option>
              <option value="ollama">Ollama Local (http://localhost:11434)</option>
              <option value="openai_compatible">OpenAI-Compatible Local (LM Studio / vLLM)</option>
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="ollama-url-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            URL Servidor Local
          </label>
          <input
            id="ollama-url-input"
            type="text"
            value={ollamaUrl}
            onChange={(e) => onOllamaUrlChange(e.target.value)}
            placeholder="http://127.0.0.1:8080"
            className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-brand-300 font-mono focus:outline-none focus:border-brand-500 transition-colors shadow-inner"
          />
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="model-name-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">
            Nombre del Modelo Activo
          </label>
          <input
            id="model-name-input"
            type="text"
            value={modelName}
            onChange={(e) => onModelNameChange(e.target.value)}
            placeholder="ej. Qwen2.5-Coder-7B-Instruct-GGUF"
            className="w-full bg-dark-base/90 border border-dark-border rounded-xl px-3 py-2.5 text-xs text-indigo-300 font-mono focus:outline-none focus:border-brand-500 transition-colors shadow-inner"
          />

          {detectedModels.length > 0 && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <Radio className="w-3 h-3 text-cyan-400 animate-pulse" /> Modelos Detectados:
              </span>
              {detectedModels.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => onModelNameChange(m)}
                  className={`text-[10px] font-mono px-2.5 py-1 rounded-lg transition-all border ${
                    modelName === m
                      ? 'bg-brand-500/20 text-brand-300 border-brand-500/40 font-bold shadow-sm'
                      : 'bg-dark-base/60 text-gray-400 hover:text-white border-dark-border hover:border-gray-600'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Test Feedback Banner */}
      {llmTestResult && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
            llmTestResult.success
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {llmTestResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" /> : <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />}
          <span className="font-medium">{llmTestResult.message} ({llmTestResult.latency_ms} ms)</span>
        </div>
      )}
    </div>
  );
};
