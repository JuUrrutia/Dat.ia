import React from 'react';
import {
  Sliders,
  Eye,
  TrendingUp,
  Hash,
  Download,
  Table as TableIcon,
  Check,
} from 'lucide-react';
import { ColorTheme, THEME_COLORS } from '../executiveDashboardUtils';

interface StudioChartToolbarProps {
  sortOrder: 'default' | 'desc' | 'asc';
  setSortOrder: (order: 'default' | 'desc' | 'asc') => void;
  showDataLabels: boolean;
  setShowDataLabels: (show: boolean | ((prev: boolean) => boolean)) => void;
  showAverageLine: boolean;
  setShowAverageLine: (show: boolean | ((prev: boolean) => boolean)) => void;
  showDataZoom: boolean;
  setShowDataZoom: (show: boolean | ((prev: boolean) => boolean)) => void;
  colorTheme: ColorTheme;
  setColorTheme: (theme: ColorTheme) => void;
  onDownloadPng: () => void;
  onViewTable: () => void;
}

export const StudioChartToolbar: React.FC<StudioChartToolbarProps> = ({
  sortOrder,
  setSortOrder,
  showDataLabels,
  setShowDataLabels,
  showAverageLine,
  setShowAverageLine,
  showDataZoom,
  setShowDataZoom,
  colorTheme,
  setColorTheme,
  onDownloadPng,
  onViewTable,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-1 text-xs text-zinc-400">
      {/* Left Controls: Sort Order & Toggles */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Sort Order */}
        <div className="flex items-center space-x-1.5">
          <span className="flex items-center space-x-1 text-zinc-400 font-medium">
            <Sliders className="w-3.5 h-3.5" />
            <span>Orden:</span>
          </span>
          <div className="flex items-center space-x-1">
            {(['default', 'desc', 'asc'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setSortOrder(mode)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                  sortOrder === mode
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold'
                    : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border border-white/5'
                }`}
              >
                {mode === 'default' ? 'Natural' : mode === 'desc' ? 'Mayor a Menor' : 'Menor a Mayor'}
              </button>
            ))}
          </div>
        </div>

        {/* Toggles: Data Labels & Average Line */}
        <div className="flex items-center space-x-1.5 border-l border-white/10 pl-3">
          <button
            type="button"
            onClick={() => setShowDataLabels((prev) => !prev)}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors border ${
              showDataLabels
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30 font-semibold'
                : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border-white/5'
            }`}
            title="Mostrar etiquetas numéricas en cada punto/barra"
          >
            <Eye className="w-3 h-3" />
            <span>Etiquetas</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAverageLine((prev) => !prev)}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors border ${
              showAverageLine
                ? 'bg-purple-500/20 text-purple-300 border-purple-500/30 font-semibold'
                : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border-white/5'
            }`}
            title="Mostrar línea de referencia de promedio"
          >
            <TrendingUp className="w-3 h-3" />
            <span>Línea Media</span>
          </button>

          <button
            type="button"
            onClick={() => setShowDataZoom((prev) => !prev)}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors border ${
              showDataZoom
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30 font-semibold'
                : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border-white/5'
            }`}
            title="Activar deslizador de zoom temporal"
          >
            <Hash className="w-3 h-3" />
            <span>Zoom</span>
          </button>
        </div>
      </div>

      {/* Right Controls: Palettes & Download Button */}
      <div className="flex items-center space-x-3">
        {/* Color Themes */}
        <div className="flex items-center space-x-1.5">
          <span className="text-[11px] text-zinc-400 font-medium">Paleta:</span>
          <div className="flex items-center space-x-1">
            {(['amber', 'cyan', 'emerald', 'indigo', 'rose', 'ocean', 'rainbow'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setColorTheme(t)}
                className={`w-4 h-4 sm:w-5 sm:h-5 rounded-full transition-transform flex items-center justify-center ${
                  colorTheme === t ? 'ring-2 ring-white scale-110 shadow-lg' : 'opacity-60 hover:opacity-100'
                }`}
                style={{
                  backgroundColor: THEME_COLORS[t].primary,
                }}
                title={THEME_COLORS[t].name}
                aria-label={`Paleta ${THEME_COLORS[t].name}`}
              >
                {colorTheme === t && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
              </button>
            ))}
          </div>
        </div>

        {/* Action: Download PNG */}
        <div className="flex items-center space-x-1.5 border-l border-white/10 pl-3">
          <button
            type="button"
            onClick={onDownloadPng}
            className="flex items-center space-x-1 text-xs text-zinc-300 hover:text-white bg-zinc-950 hover:bg-zinc-800 border border-white/10 px-3 py-1 rounded-xl transition-colors shadow-sm"
            title="Descargar gráfico en alta resolución PNG"
          >
            <Download className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">Descargar PNG HD</span>
          </button>

          <button
            type="button"
            onClick={onViewTable}
            className="flex items-center space-x-1 text-xs text-zinc-300 hover:text-white bg-zinc-950 hover:bg-zinc-800 border border-white/10 px-3 py-1 rounded-xl transition-colors shadow-sm"
            title="Ver datos en cuadrícula tabular"
          >
            <TableIcon className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Tabla</span>
          </button>
        </div>
      </div>
    </div>
  );
};
