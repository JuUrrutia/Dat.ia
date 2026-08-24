import React, { useRef } from 'react';
import { QueryResult } from '../../types';
import { InteractiveChart, InteractiveChartRef } from './InteractiveChart';
import {
  ChartType,
  ColorTheme,
  computeChartStats,
} from './executiveDashboardUtils';
import {
  Sparkles,
  ArrowUpRight,
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
} from 'lucide-react';
import { StudioHeroAndGauges } from './studio/StudioHeroAndGauges';
import { StudioChartToolbar } from './studio/StudioChartToolbar';
import { StudioStatsStrip } from './studio/StudioStatsStrip';

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
        <StudioHeroAndGauges
          result={result}
          totalVal={totalVal}
          maxValRow={maxValRow}
          numCol={numCol}
          catCol={catCol}
          currentTheme={currentTheme}
          formatNumber={formatNumber}
        />
      )}

      {/* Main Chart Card */}
      {showChart && (
        <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-4 sm:p-6 shadow-2xl space-y-5">
          {/* Chart Header & Chart Type Selector */}
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
          <StudioStatsStrip stats={stats} formatNumber={formatNumber} />

          {/* Controls Bar: Sorting, Palettes, Toggles & Export */}
          <StudioChartToolbar
            sortOrder={sortOrder}
            setSortOrder={setSortOrder}
            showDataLabels={showDataLabels}
            setShowDataLabels={setShowDataLabels}
            showAverageLine={showAverageLine}
            setShowAverageLine={setShowAverageLine}
            showDataZoom={showDataZoom}
            setShowDataZoom={setShowDataZoom}
            colorTheme={colorTheme}
            setColorTheme={setColorTheme}
            onDownloadPng={handleDownloadPng}
            onViewTable={() => setViewMode('table')}
          />

          {/* Interactive Chart Canvas */}
          <div className="w-full pt-2">
            <InteractiveChart ref={chartRef} option={dynamicChartOption} height="390px" />
          </div>
        </div>
      )}
    </div>
  );
};
