import React from 'react';
import { useAuth } from '../features/auth/context/AuthContext';
import { useSettingsDiagnostics } from '../features/settings/hooks/useSettingsDiagnostics';
import { Settings, CheckCircle2, Save, Cpu, Database, ShieldCheck, Activity } from 'lucide-react';
import { SettingsLLMSection } from '../components/settings/SettingsLLMSection';
import { SettingsInferenceSection } from '../components/settings/SettingsInferenceSection';
import { SettingsPostgresSection } from '../components/settings/SettingsPostgresSection';

export const SettingsPage: React.FC = () => {
  const { settings, updateSettings } = useAuth();
  const {
    provider,
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
    detectedModels,
    elapsedSeconds,
    handleProviderChange,
    handleTestLLMConnection,
    handleRunInferenceTest,
    handleTestPG,
    handleSave,
  } = useSettingsDiagnostics(settings, updateSettings);

  const providerLabel =
    provider === 'llama_cpp' ? 'llama.cpp' : provider === 'ollama' ? 'Ollama' : 'OpenAI Compatible';

  return (
    <div className="w-full h-full flex-1 bg-dark-base overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar pb-28 font-sans">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-5 rounded-2xl border border-white/10 shadow-2xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-brand-500/25 shrink-0">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg sm:text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
              <span>Studio de Opciones & Diagnóstico del Sistema</span>
            </h1>
            <p className="text-xs text-gray-400">
              Configuración del Motor IA Local, Base de Metadatos y Playground de Inferencia en Tiempo Real
            </p>
          </div>
        </div>

        {savedSuccess && (
          <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3.5 py-2 rounded-xl animate-fadeIn shadow-sm">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span className="font-semibold">Configuración guardada correctamente</span>
          </div>
        )}
      </div>

      {/* Main Form & Diagnostic Grid Layout (12-Columns) */}
      <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Core Engine Configuration (7 Columns) */}
        <div className="lg:col-span-7 space-y-6">
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

          {/* Section 2: PostgreSQL Metadata DB */}
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

          {/* Floating Action Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 glass-panel rounded-2xl border border-white/10 shadow-xl">
            <div className="text-xs text-gray-400 flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Los parámetros guardados tomarán efecto inmediatamente en las siguientes consultas.</span>
            </div>

            <button
              type="submit"
              className="w-full sm:w-auto flex items-center justify-center space-x-2 text-xs bg-brand-600 hover:bg-brand-500 text-white font-bold px-6 py-3 rounded-xl shadow-lg shadow-brand-600/30 transition-all glow-brand hover:scale-105 shrink-0 focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <Save className="w-4 h-4" />
              <span>Guardar Configuración</span>
            </button>
          </div>
        </div>

        {/* Right Column: Real-time Playground & Diagnostics (5 Columns) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Section 3: LLM Inference Test Playground */}
          <SettingsInferenceSection
            testPrompt={testPrompt}
            testingInference={testingInference}
            elapsedSeconds={elapsedSeconds}
            inferenceResult={inferenceResult}
            onTestPromptChange={setTestPrompt}
            onRunInferenceTest={handleRunInferenceTest}
          />

          {/* Section 4: Live System Status Summary */}
          <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4 shadow-xl">
            <div className="flex items-center space-x-2 border-b border-dark-border/80 pb-3">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Estado Actual del Servidor
              </h3>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-dark-base/60 border border-dark-border/60">
                <div className="flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  <span className="text-gray-300 font-medium">Motor Text-to-SQL</span>
                </div>
                <span className="font-mono text-[11px] text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                  {providerLabel}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-dark-base/60 border border-dark-border/60">
                <div className="flex items-center space-x-2">
                  <Database className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-300 font-medium">Base de Metadatos</span>
                </div>
                <span className="font-mono text-[11px] text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 truncate max-w-[160px]">
                  {pgDb}@{pgHost}:{pgPort}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-dark-base/60 border border-dark-border/60">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-gray-300 font-medium">Modo de Privacidad</span>
                </div>
                <span className="font-semibold text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  0 Exfiltración (Local)
                </span>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
