import React from 'react';
import { QueryResult } from '../../types';
import { InteractiveChart } from './InteractiveChart';
import {
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  BarChart3,
  Activity,
  LineChart,
  PieChart,
  Gauge,
  Sliders,
} from 'lucide-react';

export type ChartType = 'bar' | 'area' | 'line' | 'donut' | 'pie' | 'gauge';

interface ExecutiveStudioViewProps {
  result: QueryResult;
  totalVal: number;
  maxValRow: Record<string, any> | null;
  numCol: string;
  catCol: string;
  currentTheme: any;
  activeChartType: ChartType;
  setActiveChartType: (type: ChartType) => void;
  sortOrder: 'default' | 'desc' | 'asc';
  setSortOrder: (order: 'default' | 'desc' | 'asc') => void;
  colorTheme: 'amber' | 'cyan' | 'emerald' | 'indigo';
  setColorTheme: (theme: 'amber' | 'cyan' | 'emerald' | 'indigo') => void;
  dynamicChartOption: any;
  formatNumber: (num: number) => string;
  setViewMode: (mode: 'studio' | 'report' | 'table') => void;
}

export const ExecutiveStudioView: React.FC<ExecutiveStudioViewProps> = ({
  result,
  totalVal,
  maxValRow,
  numCol,
  catCol,
  currentTheme,
  activeChartType,
  setActiveChartType,
  sortOrder,
  setSortOrder,
  colorTheme,
  setColorTheme,
  dynamicChartOption,
  formatNumber,
  setViewMode,
}) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Executive Diagnosis Summary Banner */}
      <div className="bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-2xl p-4.5 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-[11px] font-bold text-amber-400 uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Diagnóstico Ejecutivo de Negocio</span>
          </div>
          <p className="text-xs text-zinc-200 leading-relaxed font-normal">
            {result.executive_report?.overview || result.summary_text}
          </p>
        </div>

        <button
          onClick={() => setViewMode('report')}
          className="text-xs text-amber-300 hover:text-white font-semibold flex items-center space-x-1.5 shrink-0 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-3.5 py-1.5 rounded-xl transition-colors shadow-sm self-start sm:self-auto"
        >
          <span>Ver Informe Completo</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Top Row: Hero Card + Radial Progress Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Widget 1: Hero Metric Card */}
        <div className={`${result.gauges && result.gauges.length > 0 ? 'lg:col-span-5' : 'lg:col-span-12'} bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between`}>
          <div
            className="absolute -top-16 -right-16 w-48 h-48 rounded-full blur-3xl pointer-events-none opacity-20"
            style={{ backgroundColor: currentTheme.primary }}
          />

          <div>
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-400 mb-2">
              <span className="uppercase tracking-wider">Métrica Principal</span>
              <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md text-[11px]">
                <TrendingUp className="w-3 h-3" />
                <span>Óptimo</span>
              </span>
            </div>

            <div className="flex items-baseline space-x-2 mt-1">
              <span className="text-4xl font-extrabold text-white tracking-tight">
                {formatNumber(totalVal || result.data_rows?.length || 0)}
              </span>
              <span className="text-xs text-zinc-400 font-medium">
                {numCol?.replace(/_/g, ' ') || 'total'}
              </span>
            </div>

            {maxValRow && (
              <div className="mt-3 flex items-center space-x-2 text-xs text-zinc-400 bg-zinc-950/50 border border-white/5 rounded-xl p-2.5">
                <ArrowUpRight className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  Líder destacado: <strong className="text-zinc-200">{String(maxValRow[catCol] || '')}</strong> ({formatNumber(Number(maxValRow[numCol]) || 0)})
                </span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 pt-5 mt-5 border-t border-white/5">
            <div>
              <div className="text-[11px] text-zinc-400 font-medium">Registros Analizados</div>
              <div className="text-lg font-bold text-white mt-0.5">
                {result.data_rows?.length || 0} filas
              </div>
            </div>
            <div>
              <div className="text-[11px] text-zinc-400 font-medium">Latencia IA</div>
              <div className="text-lg font-bold text-emerald-400 mt-0.5">
                {(((result.traceability?.execution_time_ms ?? 0)) / 1000).toFixed(2)}s
              </div>
            </div>
          </div>
        </div>

        {/* Widget 2: Metric Gauges (Only rendered if result.gauges exists and has items) */}
        {result.gauges && result.gauges.length > 0 && (
          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {result.gauges.map((gauge, gIdx) => (
              <div
                key={gIdx}
                className="bg-gradient-to-br from-zinc-900/80 via-zinc-900/40 to-zinc-950/80 border border-white/10 rounded-3xl p-6 shadow-2xl flex flex-col justify-between relative overflow-hidden"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    {gauge.title}
                  </span>
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: gauge.color || '#F59E0B' }} />
                </div>

                <div className="flex items-center justify-between my-4">
                  <div>
                    <div className="text-3xl font-extrabold text-white tracking-tight">
                      {gauge.value_label}
                    </div>
                    <div className="text-xs text-zinc-400 mt-1 font-medium">
                      {gauge.target_label}
                    </div>
                  </div>

                  <div className="relative w-20 h-20 flex items-center justify-center">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke="currentColor"
                        strokeWidth="7"
                        className="text-zinc-800"
                        fill="transparent"
                      />
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke={gauge.color || '#F59E0B'}
                        strokeWidth="7"
                        strokeDasharray={2 * Math.PI * 32}
                        strokeDashoffset={2 * Math.PI * 32 * (1 - Math.min(100, Math.max(0, gauge.percentage)) / 100)}
                        strokeLinecap="round"
                        fill="transparent"
                        className="transition-colors duration-1000 ease-out"
                      />
                    </svg>
                    <span className="absolute text-xs font-bold text-white">
                      {Math.round(gauge.percentage)}%
                    </span>
                  </div>
                </div>

                <div className="w-full bg-zinc-800/80 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-colors duration-1000"
                    style={{
                      width: `${Math.min(100, gauge.percentage)}%`,
                      backgroundColor: gauge.color || '#F59E0B'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Chart Card */}
      <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/5">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                Visualizador Dinámico de Datos
              </h3>
              <p className="text-[11px] text-zinc-400">
                Cambia la proyección visual, paleta o aplica ordenamiento dinámico
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 bg-zinc-950/80 p-1.5 rounded-2xl border border-white/5">
            {[
              { type: 'bar', label: 'Barras', icon: BarChart3 },
              { type: 'area', label: 'Área', icon: Activity },
              { type: 'line', label: 'Línea', icon: LineChart },
              { type: 'donut', label: 'Donut', icon: PieChart },
              { type: 'gauge', label: 'Gauge', icon: Gauge }
            ].map((item) => {
              const Icon = item.icon;
              const isActive = activeChartType === item.type;
              return (
                <button
                  key={item.type}
                  onClick={() => setActiveChartType(item.type as ChartType)}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                    isActive
                      ? 'bg-zinc-800 text-amber-400 border border-amber-500/30 shadow-md'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-400">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1 text-zinc-400 font-medium">
              <Sliders className="w-3.5 h-3.5" />
              <span>Orden:</span>
            </span>
            <div className="flex items-center space-x-1">
              {(['default', 'desc', 'asc'] as const).map((mode) => (
                <button
                  key={mode}
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

          <div className="flex items-center space-x-2">
            <span className="text-[11px] text-zinc-400 font-medium">Paleta:</span>
            <div className="flex items-center space-x-1.5">
              {(['amber', 'cyan', 'emerald', 'indigo'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setColorTheme(t)}
                  className={`w-5 h-5 rounded-full transition-transform ${
                    colorTheme === t ? 'ring-2 ring-white scale-110 shadow-lg' : 'opacity-60 hover:opacity-100'
                  }`}
                  style={{
                    backgroundColor:
                      t === 'amber'
                        ? '#F59E0B'
                        : t === 'cyan'
                        ? '#06B6D4'
                        : t === 'emerald'
                        ? '#10B981'
                        : '#8B5CF6'
                  }}
                  title={`Paleta ${t}`}
                  aria-label={`Paleta de color ${t}`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="w-full pt-2">
          <InteractiveChart option={dynamicChartOption} height="360px" />
        </div>
      </div>
    </div>
  );
};
