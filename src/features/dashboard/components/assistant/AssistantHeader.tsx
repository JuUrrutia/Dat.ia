import React from 'react';
import { QueryResult } from '../../../../types';
import {
  Sparkles,
  Copy,
  Check,
  Database,
  Table as TableIcon,
  BarChart3,
  ChevronDown,
  ChevronUp,
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
  onToggleSupportData,
  onCopy,
}) => {
  const hasSupportData = Boolean(result.data_rows && result.data_rows.length > 0);

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-1 pb-1">
      {/* Response Badges */}
      <div className="flex items-center space-x-2 flex-wrap gap-y-1 text-xs">
        <span className="inline-flex items-center gap-1 font-semibold text-cyan-400 bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/20 text-[10px]">
          <Sparkles className="w-3 h-3" />
          <span>Respuesta DATIA IA</span>
        </span>

        {result.grounding_info && (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            <Database className="w-3 h-3" />
            <span>Datos Reales BD</span>
          </span>
        )}
      </div>

      {/* Action Buttons: Support Data, Studio, Copy */}
      <div className="flex items-center space-x-2">
        {canSwitchToStudio && onSwitchToStudio && (
          <button
            type="button"
            onClick={onSwitchToStudio}
            className="flex items-center space-x-1 px-2.5 py-1 rounded-xl text-xs font-medium bg-dark-base hover:bg-dark-card text-brand-300 border border-brand-500/30 transition-all"
            title="Ver proyección en Studio Analítico"
          >
            <BarChart3 className="w-3.5 h-3.5 text-brand-400" />
            <span className="hidden sm:inline">Ver en Studio</span>
          </button>
        )}

        {hasSupportData && (
          <button
            type="button"
            onClick={onToggleSupportData}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-xl text-xs font-medium border transition-all ${
              showSupportData
                ? 'bg-brand-600 text-white border-brand-500 font-semibold'
                : 'bg-dark-base hover:bg-dark-card text-gray-300 border-dark-border'
            }`}
            title="Ver registros consultados en la BD"
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>Tabla de Datos ({result.data_rows?.length || 0})</span>
            {showSupportData ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}

        <button
          type="button"
          onClick={onCopy}
          className="flex items-center space-x-1 px-2.5 py-1 rounded-xl text-xs font-medium bg-dark-base hover:bg-dark-card text-gray-300 border border-dark-border hover:text-white transition-all"
          title="Copiar respuesta al portapapeles"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
        </button>
      </div>
    </div>
  );
};
