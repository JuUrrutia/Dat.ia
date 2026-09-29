import React from 'react';
import { QueryResult } from '../../../../types';
import {
  Sparkles,
  Copy,
  Check,
  BarChart3,
} from 'lucide-react';

interface AssistantHeaderProps {
  result: QueryResult;
  canSwitchToStudio: boolean;
  copied: boolean;
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
  onCopy: () => void;
}

export const AssistantHeader: React.FC<AssistantHeaderProps> = ({
  result,
  canSwitchToStudio,
  copied,
  onSwitchToStudio,
  onCopy,
}) => {
  return (
    <div className="assistant-response-header flex items-center justify-between gap-2 px-1 pb-1">
      {/* Response Badge */}
      <div className="flex items-center space-x-2 text-xs">
        <span className="inline-flex items-center gap-1.5 font-semibold text-cyan-700 dark:text-cyan-400 bg-cyan-500/15 dark:bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/30 text-[11px]">
          <Sparkles className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
          <span>Respuesta DATIA</span>
        </span>
      </div>

      {/* Action Buttons: Studio & Copy */}
      <div className="flex items-center space-x-2">
        {canSwitchToStudio && onSwitchToStudio && (
          <button
            type="button"
            onClick={onSwitchToStudio}
            className="flex items-center space-x-1 px-2.5 py-1 rounded-xl text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-card text-brand-700 dark:text-brand-300 border border-brand-500/30 transition-all shadow-xs cursor-pointer"
            title="Ver proyección en Studio Analítico"
          >
            <BarChart3 className="w-3.5 h-3.5 text-brand-600 dark:text-brand-400" />
            <span className="hidden sm:inline">Ver en Studio</span>
          </button>
        )}

        <button
          type="button"
          onClick={onCopy}
          className="flex items-center space-x-1 px-2.5 py-1 rounded-xl text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-dark-base dark:hover:bg-dark-card text-slate-700 dark:text-gray-300 border border-slate-300 dark:border-dark-border hover:text-slate-900 dark:hover:text-white transition-all shadow-xs cursor-pointer"
          title="Copiar respuesta al portapapeles"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
        </button>
      </div>
    </div>
  );
};
