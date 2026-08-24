import React from 'react';
import { QueryResult } from '../../../../types';
import {
  Sparkles,
  Copy,
  Check,
  Database,
  Lightbulb,
  Table as TableIcon,
  BarChart3,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react';

interface AssistantHeaderProps {
  result: QueryResult;
  canSwitchToStudio: boolean;
  showSupportData: boolean;
  copied: boolean;
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
  onToggleSupportData: () => void;
  onCopy: () => void;
}

export const AssistantHeader: React.FC<AssistantHeaderProps> = ({
  result,
  canSwitchToStudio,
  showSupportData,
  copied,
  onSwitchToStudio,
  onSwitchToReport,
  onToggleSupportData,
  onCopy,
}) => {
  const hasSupportData = Boolean(result.data_rows && result.data_rows.length > 0);

  return (
    <div className="bg-gradient-to-r from-zinc-900/95 via-zinc-900/70 to-zinc-950/95 border border-white/10 rounded-3xl p-6 shadow-2xl backdrop-blur-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start sm:items-center space-x-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-amber-500/20 to-amber-500/5 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10 shrink-0">
            <Lightbulb className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <h2 className="text-base font-bold text-white tracking-tight">
                {result.response_type === 'greeting'
                  ? 'Asistente DATIA'
                  : result.response_type === 'explanation'
                  ? 'Explicación Conceptual'
                  : result.response_type === 'data_analysis'
                  ? 'Respuesta Analítica IA'
                  : 'Asesoría Estratégica IA'}
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" />
                {result.response_type === 'explanation'
                  ? 'Explicación'
                  : result.response_type === 'greeting'
                  ? 'Conversación'
                  : result.response_type === 'data_analysis'
                  ? 'Interpretación de Datos'
                  : 'Estrategia'}
              </span>
              {result.grounding_info && (
                <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <Database className="w-2.5 h-2.5" />
                  <span>Datos Reales BD</span>
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              Respuesta generada para "{result.question}" a partir de la base de datos activa.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-start md:self-auto flex-wrap gap-y-2">
          {canSwitchToStudio && onSwitchToStudio && (
            <button
              onClick={onSwitchToStudio}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 hover:text-white transition-colors"
              title="Ver proyección en Studio Analítico"
            >
              <BarChart3 className="w-3.5 h-3.5 text-amber-400" />
              <span>Ver en Studio</span>
            </button>
          )}

          {result.executive_report && onSwitchToReport && (
            <button
              onClick={onSwitchToReport}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 hover:text-white transition-colors"
              title="Ver formato informe"
            >
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span>Informe</span>
            </button>
          )}

          {hasSupportData && (
            <button
              onClick={onToggleSupportData}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                showSupportData
                  ? 'bg-amber-500 text-zinc-950 border-amber-400 font-bold'
                  : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-white/10 hover:text-white'
              }`}
              title="Ver registros consultados en SQLite"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Datos de Apoyo ({result.data_rows?.length || 0})</span>
              {showSupportData ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
            </button>
          )}

          <button
            onClick={onCopy}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-colors shadow-sm"
            title="Copiar respuesta al portapapeles"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
