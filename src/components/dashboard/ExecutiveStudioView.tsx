import React, { useRef } from 'react';
import { QueryResult } from '../../types';
import { InteractiveChart, InteractiveChartRef } from './InteractiveChart';
import {
  ChartType,
  ColorTheme,
  THEME_COLORS,
  computeChartStats,
} from './executiveDashboardUtils';
import {
  Sparkles,
  ArrowUpRight,
  TrendingUp,
  BarChart3,
  AlignLeft,
  Activity,
  LineChart,
  PieChart,
  CircleDot,
  Radio,
  ScatterChart,
  Filter,
  Gauge,
  LayoutGrid,
  Sliders,
  Download,
  Eye,
  Hash,
  Table as TableIcon,
  Check,
} from 'lucide-react';

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
  colorTheme: ColorTheme;
  setColorTheme: (theme: ColorTheme) => void;
  showDataLabels: boolean;
  setShowDataLabels: (show: boolean | ((prev: boolean) => boolean)) => void;
  showAverageLine: boolean;
  setShowAverageLine: (show: boolean | ((prev: boolean) => boolean)) => void;
  showDataZoom: boolean;
  setShowDataZoom: (show: boolean | ((prev: boolean) => boolean)) => void;
  dynamicChartOption: any;
  formatNumber: (num: number) => string;
  setViewMode: (mode: 'studio' | 'report' | 'table') => void;
}

const CHART_TYPES: { type: ChartType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { type: 'bar', label: 'Barras', icon: BarChart3 },
  { type: 'horizontal_bar', label: 'Ranking (H)', icon: AlignLeft },
  { type: 'line', label: 'Línea', icon: LineChart },
  { type: 'area', label: 'Área Glow', icon: Activity },
  { type: 'donut', label: 'Donut', icon: CircleDot },
  { type: 'pie', label: 'Torta', icon: PieChart },
  { type: 'radar', label: 'Radar', icon: Radio },
  { type: 'scatter', label: 'Dispersión', icon: ScatterChart },
  { type: 'funnel', label: 'Embudo', icon: Filter },
  { type: 'gauge', label: 'Velocímetro', icon: Gauge },
  { type: 'treemap', label: 'Treemap', icon: LayoutGrid },
];

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
  showDataLabels,
  setShowDataLabels,
  showAverageLine,
  setShowAverageLine,
  showDataZoom,
  setShowDataZoom,
  dynamicChartOption,
  formatNumber,
  setViewMode,
}) => {
  const chartRef = useRef<InteractiveChartRef>(null);
  const hints = result.presentation_hints;
  const showDiagnosis = hints?.show_executive_report !== false;
  const showKpis = hints?.show_kpis !== false;
  const showChart = hints?.show_chart !== false;

  const stats = computeChartStats(result.data_rows || [], catCol, numCol);

  const handleDownloadPng = () => {
    const filename = `grafico_datia_${numCol || 'analitica'}_${Date.now()}.png`;
    chartRef.current?.downloadImage(filename);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Executive Diagnosis Summary Banner */}
      {showDiagnosis && (
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
            type="button"
            onClick={() => setViewMode('report')}
            className="text-xs text-amber-300 hover:text-white font-semibold flex items-center space-x-1.5 shrink-0 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-3.5 py-1.5 rounded-xl transition-colors shadow-sm self-start sm:self-auto"
          >
            <span>Ver Informe Completo</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top Row: Hero Card + Radial Progress Gauges */}
      {showKpis && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
          {/* Widget 1: Hero Metric Card */}
          <div className={`${result.gauges && result.gauges.length > 0 ? 'lg:col-span-5' : 'lg:col-span-12'} bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between`}>
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

              <div className="flex flex-wrap items-baseline gap-2 mt-1">
                <span className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
                  {formatNumber(totalVal || result.data_rows?.length || 0)}
                </span>
                <span className="text-xs text-zinc-400 font-medium">
                  {numCol?.replace(/_/g, ' ') || 'total'}
                </span>
              </div>

              {maxValRow && (
                <div className="mt-3 flex items-center space-x-2 text-xs text-zinc-400 bg-zinc-950/50 border border-white/5 rounded-xl p-2.5">
                  <ArrowUpRight className="w-4 h-4 text-amber-400 shrink-0" />
                  <span className="truncate">
                    Líder: <strong className="text-zinc-200">{String(maxValRow[catCol] || '')}</strong> ({formatNumber(Number(maxValRow[numCol]) || 0)})
                  </span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 pt-4 sm:pt-5 mt-4 sm:mt-5 border-t border-white/5">
              <div>
                <div className="text-[11px] text-zinc-400 font-medium">Registros Analizados</div>
                <div className="text-base sm:text-lg font-bold text-white mt-0.5">
                  {result.data_rows?.length || 0} filas
                </div>
              </div>
              <div>
                <div className="text-[11px] text-zinc-400 font-medium">Latencia IA</div>
                <div className="text-base sm:text-lg font-bold text-emerald-400 mt-0.5">
                  {(((result.traceability?.execution_time_ms ?? 0)) / 1000).toFixed(2)}s
                </div>
              </div>
            </div>
          </div>

          {/* Widget 2: Metric Gauges */}
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
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Chart Card */}
      {showChart && (
        <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-4 sm:p-6 shadow-2xl space-y-5">
          {/* Chart Header & Chart Type Segmented Pills */}
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-4 border-b border-white/5">
            <div className="flex items-center space-x-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center border shadow-sm shrink-0"
                style={{
                  backgroundColor: `${currentTheme.primary}15`,
                  borderColor: `${currentTheme.primary}30`,
                  color: currentTheme.primary,
                }}
              >
                <BarChart3 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  Visualizador Dinámico de Datos
                </h3>
                <p className="text-[11px] text-zinc-400">
                  Explora proyecciones, paletas, líneas de tendencia y descarga en HD
                </p>
              </div>
            </div>

            {/* Scrollable / Responsive Chart Type Selector Pills */}
            <div className="flex items-center gap-1.5 bg-zinc-950/90 p-1.5 rounded-2xl border border-white/5 overflow-x-auto custom-scrollbar">
              {CHART_TYPES.map((item) => {
                const Icon = item.icon;
                const isActive = activeChartType === item.type;
                return (
                  <button
                    key={item.type}
                    type="button"
                    onClick={() => setActiveChartType(item.type)}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-zinc-800 text-white border shadow-md'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
                    }`}
                    style={
                      isActive
                        ? { borderColor: `${currentTheme.primary}50`, color: currentTheme.primary }
                        : undefined
                    }
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Analytics Summary Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 p-3 rounded-2xl bg-zinc-950/60 border border-white/5">
            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <span>Total</span>
              </div>
              <div className="text-xs sm:text-sm font-bold text-white font-mono truncate">
                {formatNumber(stats.total)}
              </div>
            </div>

            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <span>Promedio</span>
              </div>
              <div className="text-xs sm:text-sm font-bold text-amber-400 font-mono truncate">
                {formatNumber(stats.avg)}
              </div>
            </div>

            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <span>Máximo</span>
              </div>
              <div className="text-xs sm:text-sm font-bold text-emerald-400 font-mono truncate" title={stats.maxLabel}>
                {formatNumber(stats.max)}
              </div>
            </div>

            <div className="space-y-0.5">
              <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <span>Mínimo</span>
              </div>
              <div className="text-xs sm:text-sm font-bold text-rose-400 font-mono truncate" title={stats.minLabel}>
                {formatNumber(stats.min)}
              </div>
            </div>

            <div className="space-y-0.5 col-span-2 sm:col-span-1">
              <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                <span>Muestras</span>
              </div>
              <div className="text-xs sm:text-sm font-bold text-cyan-400 font-mono truncate">
                {stats.count} registros
              </div>
            </div>
          </div>

          {/* Controls Bar: Sorting, Palettes, Toggles & Export */}
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
                  onClick={handleDownloadPng}
                  className="flex items-center space-x-1 text-xs text-zinc-300 hover:text-white bg-zinc-950 hover:bg-zinc-800 border border-white/10 px-3 py-1 rounded-xl transition-colors shadow-sm"
                  title="Descargar gráfico en alta resolución PNG"
                >
                  <Download className="w-3.5 h-3.5 text-amber-400" />
                  <span className="hidden sm:inline">Descargar PNG HD</span>
                </button>

                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  className="flex items-center space-x-1 text-xs text-zinc-300 hover:text-white bg-zinc-950 hover:bg-zinc-800 border border-white/10 px-3 py-1 rounded-xl transition-colors shadow-sm"
                  title="Ver datos en cuadrícula tabular"
                >
                  <TableIcon className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">Tabla</span>
                </button>
              </div>
            </div>
          </div>

          {/* Interactive Chart Canvas */}
          <div className="w-full pt-2">
            <InteractiveChart ref={chartRef} option={dynamicChartOption} height="390px" />
          </div>
        </div>
      )}
    </div>
  );
};
