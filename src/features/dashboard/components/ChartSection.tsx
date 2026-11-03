import React, { useState, useRef, useMemo, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { QueryResult } from '../../../types';
import { THEME_COLORS, ColorTheme, ChartType, prefersReducedMotion } from './charts/theme';
import { buildDynamicChartOption, deriveProcessedRows } from '../../../components/dashboard/executiveDashboardUtils';
import {
  BarChart3,
  TrendingUp,
  PieChart,
  Layers,
  AlignLeft,
  Copy,
  Check,
  ChevronDown,
  CircleDot,
  Gauge,
  LayoutGrid,
  Radar,
} from 'lucide-react';

interface ChartSectionProps {
  result: QueryResult;
  colorTheme?: ColorTheme;
  onDrillDown?: (category: string) => void;
  onTimeFilter?: (filterLabel: string) => void;
}

interface ChartTypeOption {
  id: ChartType;
  label: string;
  group: string;
  icon: React.FC<{ className?: string }>;
}

// El orden de los grupos es el que se renderiza. `pie` ya tenía builder
// (pieChartConfig) pero nunca estuvo expuesto en la barra de morphing.
const AVAILABLE_CHART_TYPES: ChartTypeOption[] = [
  { id: 'bar', label: 'Barras', group: 'Comparar', icon: BarChart3 },
  { id: 'horizontal_bar', label: 'Horizontal', group: 'Comparar', icon: AlignLeft },
  { id: 'radial', label: 'Radial', group: 'Comparar', icon: Radar },
  { id: 'scatter', label: 'Dispersión', group: 'Comparar', icon: CircleDot },
  { id: 'line', label: 'Líneas', group: 'Tendencia', icon: TrendingUp },
  { id: 'area', label: 'Área', group: 'Tendencia', icon: Layers },
  { id: 'pie', label: 'Torta', group: 'Composición', icon: PieChart },
  { id: 'donut', label: 'Donut', group: 'Composición', icon: PieChart },
  { id: 'treemap', label: 'Treemap', group: 'Composición', icon: LayoutGrid },
  { id: 'gauge', label: 'Medidor', group: 'KPI', icon: Gauge },
];

const CHART_GROUP_ORDER = ['Comparar', 'Tendencia', 'Composición', 'KPI'];
const CHART_TYPE_STORAGE_KEY = 'datia-chart-type';

const isKnownChartType = (id: unknown): id is ChartType =>
  typeof id === 'string' && AVAILABLE_CHART_TYPES.some((ct) => ct.id === id);

const CURRENT_YEAR = new Date().getFullYear();

const TIME_FILTER_OPTIONS = [
  { id: 'all', label: 'Todo' },
  { id: 'month', label: 'Este Mes' },
  { id: 'qtr', label: 'Últimos 90 Días' },
  { id: String(CURRENT_YEAR), label: `Año ${CURRENT_YEAR}` },
  { id: String(CURRENT_YEAR - 1), label: `Año ${CURRENT_YEAR - 1}` },
];

export const ChartSection: React.FC<ChartSectionProps> = ({
  result,
  colorTheme = 'indigo',
  onDrillDown,
  onTimeFilter,
}) => {
  const [activeChartType, setActiveChartType] = useState<ChartType>(() => {
    const backendType = result.chart_type as ChartType;
    if (typeof window !== 'undefined') {
      try {
        const saved = window.localStorage.getItem(CHART_TYPE_STORAGE_KEY);
        if (isKnownChartType(saved)) return saved;
      } catch {
        // localStorage bloqueado (modo privado / iframe): usar el del backend.
      }
    }
    return isKnownChartType(backendType) ? backendType : 'bar';
  });
  const [activeTimeFilter, setActiveTimeFilter] = useState<string>('all');
  const [copiedChart, setCopiedChart] = useState(false);
  const [chartMenuOpen, setChartMenuOpen] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartMenuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (chartMenuRef.current && !chartMenuRef.current.contains(e.target as Node)) {
        setChartMenuOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setChartMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [chartMenuOpen]);

  const handleSelectChartType = (id: ChartType) => {
    setActiveChartType(id);
    setChartMenuOpen(false);
    try {
      window.localStorage.setItem(CHART_TYPE_STORAGE_KEY, id);
    } catch {
      // Sin persistencia: el tipo sigue válido en esta sesión.
    }
  };

  const handleCopyChart = async () => {
    if (!chartContainerRef.current) return;
    try {
      let blob: Blob | null = null;
      const canvasEl = chartContainerRef.current.querySelector('canvas') as HTMLCanvasElement | null;

      if (canvasEl) {
        const offscreen = document.createElement('canvas');
        offscreen.width = canvasEl.width;
        offscreen.height = canvasEl.height;
        const ctx = offscreen.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#18181B'; // Clean corporate dark background
          ctx.fillRect(0, 0, offscreen.width, offscreen.height);
          ctx.drawImage(canvasEl, 0, 0);
          blob = await new Promise<Blob | null>((resolve) => offscreen.toBlob(resolve, 'image/png'));
        } else {
          blob = await new Promise<Blob | null>((resolve) => canvasEl.toBlob(resolve, 'image/png'));
        }
      } else {
        const svgEl = chartContainerRef.current.querySelector('svg') as SVGElement | null;
        if (svgEl) {
          const svgString = new XMLSerializer().serializeToString(svgEl);
          const dataUri = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(svgString)));
          const img = new Image();
          const svgRect = svgEl.getBoundingClientRect();
          const width = Math.max(svgRect.width || 600, 600) * 2;
          const height = Math.max(svgRect.height || 360, 360) * 2;
          blob = await new Promise<Blob | null>((resolve) => {
            img.onload = () => {
              const canvas = document.createElement('canvas');
              canvas.width = width;
              canvas.height = height;
              const ctx = canvas.getContext('2d');
              if (ctx) {
                ctx.fillStyle = '#18181B';
                ctx.fillRect(0, 0, width, height);
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob(resolve, 'image/png');
              } else {
                resolve(null);
              }
            };
            img.onerror = () => resolve(null);
            img.src = dataUri;
          });
        }
      }

      if (blob && navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        setCopiedChart(true);
        setTimeout(() => setCopiedChart(false), 2000);
      }
    } catch (err) {
      console.error('No se pudo copiar el gráfico al portapapeles:', err);
    }
  };

  if (
    !result.chart_type ||
    result.chart_type === 'none' ||
    !result.data_rows ||
    result.data_rows.length === 0
  ) {
    return null;
  }

  const currentTheme = THEME_COLORS[colorTheme] || THEME_COLORS.indigo;

  // Rebuilt on every render before. Combined with notMerge on the ECharts
  // instance, each render forced a full setOption (destroy/recreate of every
  // series) — once per second per chart while the page's elapsed-seconds timer
  // ticked. animation is JS-driven, so prefers-reduced-motion in globals.css
  // never reached the canvas.
  const { finalOption } = useMemo(() => {
    const { catCol, numCol, processedRows } = deriveProcessedRows(result, 'default');
    const isCurrency = Boolean(
      numCol &&
        (numCol.includes('ingreso') ||
          numCol.includes('monto') ||
          numCol.includes('precio') ||
          numCol.includes('costo') ||
          numCol.includes('total'))
    );
    const totalVal = processedRows.reduce((sum, r) => sum + (Number(r[numCol]) || 0), 0);

    const option = buildDynamicChartOption({
      processedRows,
      catCol,
      numCol,
      activeChartType,
      currentTheme,
      isCurrency,
      totalVal,
      fallbackChartOption: result.chart_option,
    });

    return { finalOption: { ...option, animation: !prefersReducedMotion() } };
  }, [result, activeChartType, currentTheme, colorTheme]);

  const handleChartClick = (params: any) => {
    const category = params?.name || params?.seriesName;
    if (category && onDrillDown) {
      onDrillDown(category);
    }
  };

  const handleSelectTimeFilter = (filterId: string, filterLabel: string) => {
    setActiveTimeFilter(filterId);
    if (onTimeFilter) {
      onTimeFilter(filterLabel);
    }
  };

  return (
    <div ref={chartContainerRef} className="bg-white dark:bg-zinc-900/90 border border-slate-200 dark:border-white/10 rounded-3xl p-6 shadow-xl space-y-4">
      {/* Chart Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-white/10 pb-4">
        <div>
          <h3 className="text-sm font-bold text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 dark:bg-amber-400 animate-pulse" />
            Visualización Analítica Proyectada
          </h3>
          <p className="text-xs text-slate-600 dark:text-zinc-400 mt-0.5">
            Gráfico dinámico (
            {AVAILABLE_CHART_TYPES.find((ct) => ct.id === activeChartType)?.label ?? activeChartType}) • Clic en
            elementos para desglose interactivo
          </p>
        </div>

        {/* Action Controls: Chart Morpher + Theme Selector + Copy Chart */}
        <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
          {/* Chart Morph Dropdown */}
          <div ref={chartMenuRef} className="relative">
            <button
              type="button"
              onClick={() => setChartMenuOpen((prev) => !prev)}
              aria-haspopup="listbox"
              aria-expanded={chartMenuOpen}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-zinc-950 border border-slate-200 dark:border-white/10 text-xs font-semibold text-slate-700 dark:text-zinc-200 hover:border-slate-300 dark:hover:border-white/20 transition-all"
              title="Cambiar tipo de gráfico"
            >
              {(() => {
                const Current = AVAILABLE_CHART_TYPES.find((ct) => ct.id === activeChartType)?.icon ?? BarChart3;
                return <Current className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
              })()}
              <span className="text-[11px]">
                {AVAILABLE_CHART_TYPES.find((ct) => ct.id === activeChartType)?.label ?? 'Gráfico'}
              </span>
              <ChevronDown
                className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${chartMenuOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {chartMenuOpen && (
              <div
                role="listbox"
                className="absolute right-0 top-full mt-1.5 z-50 w-[22rem] max-w-[calc(100vw-2rem)] p-2 rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-white/10 shadow-2xl"
              >
                {CHART_GROUP_ORDER.map((group, gi) => (
                  <div key={group}>
                    {gi > 0 && (
                      <div className="my-1.5 border-t border-slate-200 dark:border-white/10" />
                    )}
                    <p className="px-2 pt-1 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-zinc-500">
                      {group}
                    </p>
                    <div className="grid grid-cols-2 gap-0.5">
                      {AVAILABLE_CHART_TYPES.filter((ct) => ct.group === group).map((ct) => {
                        const Icon = ct.icon;
                        const isSelected = activeChartType === ct.id;
                        return (
                          <button
                            key={ct.id}
                            type="button"
                            role="option"
                            aria-selected={isSelected}
                            onClick={() => handleSelectChartType(ct.id)}
                            className={`flex items-center space-x-2 px-2 py-1.5 rounded-lg text-left text-xs font-semibold transition-all ${
                              isSelected
                                ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                                : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 border border-transparent'
                            }`}
                          >
                            <Icon className="w-3.5 h-3.5 shrink-0" />
                            <span className="text-[11px] truncate">{ct.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Copy Chart Image Button */}
          <button
            type="button"
            onClick={handleCopyChart}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all ${
              copiedChart
                ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40 shadow-xs'
                : 'bg-slate-100 dark:bg-zinc-950 text-slate-700 dark:text-zinc-300 hover:text-slate-900 dark:hover:text-white border-slate-300 dark:border-white/10 hover:border-slate-400 dark:hover:border-white/20 hover:bg-slate-200 dark:hover:bg-zinc-800'
            }`}
            title="Copiar gráfico al portapapeles como imagen PNG"
          >
            {copiedChart ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>¡Copiado!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-500 dark:text-zinc-400" />
                <span className="hidden sm:inline">Copiar Gráfico</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quick Time Filter Chips */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex items-center space-x-1.5">
          <span className="text-[11px] font-medium text-slate-500 dark:text-zinc-500 mr-1">Rango rápido:</span>
          {TIME_FILTER_OPTIONS.map((tf) => (
            <button
              key={tf.id}
              type="button"
              onClick={() => handleSelectTimeFilter(tf.id, tf.label)}
              className={`px-2.5 py-1 rounded-lg text-xs transition-all ${
                activeTimeFilter === tf.id
                  ? 'bg-brand-500/15 dark:bg-zinc-800 text-brand-700 dark:text-cyan-300 font-semibold border border-brand-500/30 dark:border-cyan-500/30'
                  : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-zinc-800/60 border border-transparent'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-slate-500 dark:text-zinc-500 italic">
          💡 Clic en barras/dona para desglose automático
        </span>
      </div>

      {/* ECharts Canvas with Click Event Listener */}
      <div className="w-full h-80 sm:h-96">
        <ReactECharts
          option={finalOption}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
          onEvents={{
            click: handleChartClick,
          }}
        />
      </div>
    </div>
  );
};
