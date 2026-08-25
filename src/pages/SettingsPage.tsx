import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useSettingsDiagnostics } from '../features/settings/hooks/useSettingsDiagnostics';
import { Settings, CheckCircle2, Save } from 'lucide-react';
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
