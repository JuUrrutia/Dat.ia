import React, { useState, useRef, useEffect } from 'react';
import { Send, Database, ShieldCheck, Cpu, Wand2, X, Check } from 'lucide-react';

interface ChatPromptInputProps {
  promptInput: string;
  setPromptInput: (val: string) => void;
  isGenerating: boolean;
  userRole: string;
  activeDatabaseName?: string;
  textareaRef?: React.RefObject<HTMLTextAreaElement>;
  onSubmit: () => void;
}

export const ChatPromptInput: React.FC<ChatPromptInputProps> = ({
  promptInput,
  setPromptInput,
  isGenerating,
  userRole,
  activeDatabaseName = 'BD Corporativa Local',
  textareaRef: externalTextareaRef,
  onSubmit,
}) => {
  const internalTextareaRef = useRef<HTMLTextAreaElement>(null);
  const activeTextareaRef = externalTextareaRef || internalTextareaRef;

  // Smart Query Builder state
  const [showBuilder, setShowBuilder] = useState(false);
  const [metric, setMetric] = useState('ventas totales');
  const [dimension, setDimension] = useState('por mes');
  const [period, setPeriod] = useState('este año');

  // Auto-resize textarea height
  useEffect(() => {
    if (activeTextareaRef.current) {
      activeTextareaRef.current.style.height = 'auto';
      activeTextareaRef.current.style.height = `${Math.min(activeTextareaRef.current.scrollHeight, 180)}px`;
    }
  }, [promptInput, activeTextareaRef]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (promptInput.trim() && !isGenerating) {
        onSubmit();
      }
    }
  };

  const handleApplyBuilder = () => {
    const generated = `Muestra las ${metric} agrupadas ${dimension} para ${period} con análisis detallado y gráfico`;
    setPromptInput(generated);
    setShowBuilder(false);
    if (activeTextareaRef.current) {
      activeTextareaRef.current.focus();
    }
  };

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-3 border border-white/10 shadow-2xl space-y-2.5 font-sans relative group transition-all">
      {/* Collapsible Smart Query Builder */}
      {showBuilder && (
        <div className="p-3 rounded-2xl bg-zinc-900/95 border border-indigo-500/30 shadow-xl space-y-3 animate-fadeIn">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
            <div className="flex items-center space-x-2 text-indigo-300 text-xs font-semibold">
              <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>Smart Query Builder (Asistente Guiado en 3 Pasos)</span>
            </div>
            <button
              type="button"
              onClick={() => setShowBuilder(false)}
              className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 text-xs">
            {/* Step 1: Metric */}
            <div>
              <span className="text-zinc-400 text-[11px] font-medium mr-2">1. Métrica:</span>
              <div className="inline-flex flex-wrap gap-1.5 mt-1">
                {[
                  { label: 'Ventas', val: 'ventas totales' },
                  { label: 'Margen de Utilidad', val: 'margen de utilidad' },
                  { label: 'Costos Operativos', val: 'costos operativos' },
                  { label: 'Incidentes TI', val: 'incidentes de infraestructura' },
                  { label: 'Carga de Servidores', val: 'consumo de CPU y memoria RAM de servidores' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => setMetric(item.val)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                      metric === item.val
                        ? 'bg-indigo-600 text-white shadow-xs'
                        : 'bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 2: Dimension */}
            <div>
              <span className="text-zinc-400 text-[11px] font-medium mr-2">2. Agrupación:</span>
              <div className="inline-flex flex-wrap gap-1.5 mt-1">
                {[
                  { label: 'Por Mes', val: 'por mes' },
                  { label: 'Por Categoría', val: 'por categoría de producto' },
                  { label: 'Por Sucursal / Datacenter', val: 'por sucursal' },
                  { label: 'Por Cliente', val: 'por cliente principal' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => setDimension(item.val)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                      dimension === item.val
                        ? 'bg-cyan-600 text-white shadow-xs'
                        : 'bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 3: Period */}
            <div>
              <span className="text-zinc-400 text-[11px] font-medium mr-2">3. Período:</span>
              <div className="inline-flex flex-wrap gap-1.5 mt-1">
                {[
                  { label: 'Este Año (2024)', val: 'el año 2024' },
                  { label: 'Últimos 90 Días', val: 'los últimos 90 días' },
                  { label: 'Todo el Histórico', val: 'todo el histórico' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => setPeriod(item.val)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                      period === item.val
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-zinc-800 text-[11px]">
            <span className="text-zinc-400 truncate max-w-sm">
              Previa: <i className="text-zinc-300">"Muestra las {metric} {dimension} para {period}..."</i>
            </span>
            <button
              type="button"
              onClick={handleApplyBuilder}
              className="flex items-center space-x-1 px-3 py-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors shadow-md shadow-indigo-600/30"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Insertar en Prompt</span>
            </button>
          </div>
        </div>
      )}

      {/* Auto-resizing Textarea */}
      <div className="relative">
        <textarea
          ref={activeTextareaRef}
          rows={2}
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Consulta a Dat.ia en lenguaje natural (ej: 'Ventas de productos en Q3 por región')...`}
          disabled={isGenerating}
          aria-label="Pregunta analítica sobre datos corporativos"
          className="w-full bg-dark-base/80 text-xs sm:text-sm text-white placeholder-gray-500 rounded-xl px-3.5 py-2.5 resize-none focus:outline-none transition-colors scrollbar-thin scrollbar-thumb-dark-border font-sans leading-relaxed"
        />
      </div>

      {/* Toolbar & Action Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 pt-1 border-t border-dark-border/60">
        {/* Left Items: Active DB Badge & Model Pill */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Smart Builder Toggle Button */}
          <button
            type="button"
            onClick={() => setShowBuilder((prev) => !prev)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-xl border text-[11px] font-semibold transition-colors shadow-xs ${
              showBuilder
                ? 'bg-indigo-600 text-white border-indigo-500'
                : 'bg-dark-base hover:bg-indigo-950/40 text-indigo-300 border-indigo-500/30 hover:border-indigo-500/50'
            }`}
            title="Abrir Asistente Guiado de Consultas en 3 Pasos"
          >
            <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Smart Builder</span>
          </button>

          {/* Active Database Badge */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-xl bg-dark-base/90 border border-dark-border/80 text-[11px] font-medium text-gray-300 shadow-xs">
            <Database className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="truncate max-w-[140px] sm:max-w-[200px] font-semibold">{activeDatabaseName}</span>
          </div>


          {/* AI Model & Privacy Badge */}
          <span className="hidden sm:flex items-center space-x-1 px-2.5 py-1 rounded-xl bg-purple-500/10 border border-purple-500/20 text-[10px] text-purple-300 font-medium">
            <Cpu className="w-3 h-3 text-purple-400 shrink-0" />
            <span className="relative flex h-1.5 w-1.5 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            <span>IA Local (Text-to-SQL)</span>
          </span>

          {/* RBAC Badge */}
          <span className="hidden md:flex items-center space-x-1 text-[10px] text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-xl border border-indigo-500/20 font-medium">
            <ShieldCheck className="w-3 h-3 text-indigo-400 shrink-0" />
            <span>RBAC: {userRole}</span>
          </span>
        </div>

        {/* Right Action: Send Button (Kokonut UI Circular Glow Button) */}
        <div className="flex items-center space-x-2">
          <span className="hidden sm:inline text-[10px] text-gray-500">Enter ↵</span>
          <button
            type="button"
            onClick={() => {
              if (promptInput.trim() && !isGenerating) {
                onSubmit();
              }
            }}
            disabled={!promptInput.trim() || isGenerating}
            aria-label="Enviar consulta a Dat.ia"
            title="Enviar consulta"
            className="p-2.5 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white disabled:opacity-30 disabled:pointer-events-none transition-all shadow-md shadow-brand-600/30 glow-brand hover:scale-105"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
