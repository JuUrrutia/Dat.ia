import React from 'react';
import { Sparkles, Play, Code2, CheckCircle2, AlertCircle, Terminal, Zap } from 'lucide-react';
import { LLMCompletionTestResult } from '../../features/chat/services/llm_service';

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
    <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4 shadow-xl font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dark-border/80 pb-3.5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-600/20 to-indigo-600/20 text-purple-400 border border-purple-500/30 shadow-md">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span>Playground de Inferencia Text-to-SQL</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                <Zap className="w-3 h-3 text-purple-400" /> Real-time Test
              </span>
            </h3>
            <p className="text-[11px] text-gray-400">Prueba directa de velocidad y traducción SQL contra el modelo activo</p>
          </div>
        </div>
      </div>

      {/* Prompt Textarea */}
      <div className="space-y-2">
        <label htmlFor="test-prompt-input" className="block text-[11px] font-bold uppercase tracking-wider text-gray-400">
          Consulta de Prueba (Prompt)
        </label>
        <textarea
          id="test-prompt-input"
          value={testPrompt}
          onChange={(e) => onTestPromptChange(e.target.value)}
          rows={3}
          placeholder="Escribe la consulta que deseas testear contra el modelo..."
          className="w-full bg-dark-base/90 border border-dark-border rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors shadow-inner font-sans"
        />
      </div>

      {/* Run Action */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onRunInferenceTest}
          disabled={testingInference || !testPrompt.trim()}
          className="w-full sm:w-auto flex items-center justify-center space-x-2 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-purple-600/30 transition-all glow-brand disabled:opacity-40 disabled:pointer-events-none hover:scale-[1.02]"
        >
          <Play className={`w-4 h-4 ${testingInference ? 'animate-spin' : ''}`} />
          <span>{testingInference ? `Ejecutando Inferencia... (${elapsedSeconds}s)` : 'Ejecutar Test de Inferencia'}</span>
        </button>
      </div>

      {/* Terminal / Code Output Console */}
      {inferenceResult && (
        <div className="space-y-3 pt-2 animate-fadeIn">
          <div
            className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
              inferenceResult.success
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
          >
            <div className="flex items-center space-x-2">
              {inferenceResult.success ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              )}
              <span className="font-semibold">{inferenceResult.message}</span>
            </div>
            <span className="font-mono text-[11px] bg-dark-base px-2.5 py-1 rounded-md border border-dark-border text-gray-300">
              {inferenceResult.latency_ms} ms
            </span>
          </div>

          {inferenceResult.success && inferenceResult.completion_text && (
            <div className="bg-dark-base/90 border border-dark-border/80 rounded-xl p-4 space-y-2 shadow-inner">
              <div className="flex items-center justify-between text-xs font-bold text-purple-300 border-b border-dark-border/60 pb-2">
                <div className="flex items-center space-x-2">
                  <Terminal className="w-4 h-4 text-purple-400" />
                  <span>Consola de Salida SQL Generada:</span>
                </div>
                <span className="text-[10px] text-gray-500 font-mono">ANSI SQL</span>
              </div>
              <pre className="text-xs text-emerald-300 font-mono bg-dark-surface/90 p-3.5 rounded-lg border border-dark-border/80 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {inferenceResult.completion_text}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
