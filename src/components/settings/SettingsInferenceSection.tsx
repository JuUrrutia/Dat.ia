import React from 'react';
import { Sparkles, Play, Code2, CheckCircle2, AlertCircle } from 'lucide-react';
import { LLMCompletionTestResult } from '../../services/llm_service';

interface SettingsInferenceSectionProps {
  testPrompt: string;
  testingInference: boolean;
  elapsedSeconds: number;
  inferenceResult: LLMCompletionTestResult | null;
  onTestPromptChange: (val: string) => void;
  onRunInferenceTest: () => void;
}

export const SettingsInferenceSection: React.FC<SettingsInferenceSectionProps> = ({
  testPrompt,
  testingInference,
  elapsedSeconds,
  inferenceResult,
  onTestPromptChange,
  onRunInferenceTest,
}) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      <div className="flex items-center justify-between border-b border-dark-border pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Prueba Real de Inferencia Text-to-SQL</h3>
            <p className="text-xs text-gray-400">Ejecuta una consulta de prueba directamente contra el modelo seleccionado</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onRunInferenceTest}
          disabled={testingInference || !testPrompt.trim()}
          className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors disabled:opacity-50"
        >
          <Play className={`w-3.5 h-3.5 ${testingInference ? 'animate-spin' : ''}`} />
          <span>{testingInference ? `Procesando Inferencia... (${elapsedSeconds}s)` : 'Probar Inferencia Real'}</span>
        </button>
      </div>

      <div className="space-y-3">
        <label htmlFor="test-prompt-input" className="block text-xs font-semibold text-gray-300">Consulta de Prueba</label>
        <textarea
          id="test-prompt-input"
          value={testPrompt}
          onChange={(e) => onTestPromptChange(e.target.value)}
          rows={2}
          className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500 font-sans"
        />
      </div>

      {inferenceResult && (
        <div className="space-y-3 pt-2">
          <div
            className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
              inferenceResult.success
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
            }`}
          >
            <div className="flex items-center space-x-2">
              {inferenceResult.success ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
              <span>{inferenceResult.message}</span>
            </div>
            <span className="font-mono text-[11px] bg-dark-base px-2 py-0.5 rounded border border-white/10">
              {inferenceResult.latency_ms} ms
            </span>
          </div>

          {inferenceResult.success && inferenceResult.completion_text && (
            <div className="bg-dark-base border border-dark-border rounded-xl p-4 space-y-2">
              <div className="flex items-center space-x-2 text-xs font-semibold text-purple-400">
                <Code2 className="w-4 h-4" />
                <span>Respuesta Generada por el Modelo:</span>
              </div>
              <pre className="text-xs text-gray-200 font-mono bg-dark-card p-3 rounded-lg border border-dark-border overflow-x-auto whitespace-pre-wrap">
                {inferenceResult.completion_text}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
