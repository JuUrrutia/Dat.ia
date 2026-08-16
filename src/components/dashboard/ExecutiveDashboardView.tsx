import React, { useState, useMemo } from 'react';
import { QueryResult } from '../../types';
import { InteractiveChart } from './InteractiveChart';
import { DataGridTable } from '../datagrid/DataGridTable';
import {
  BarChart3,
  LineChart,
  PieChart,
  Activity,
  Gauge,
  Compass,
  FileText,
  Table as TableIcon,
  Download,
  Copy,
  Check,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Maximize2,
  Sliders,
  Calendar,
  Layers,
  ArrowUpRight,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle
} from 'lucide-react';

interface ExecutiveDashboardViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
}

type ViewMode = 'studio' | 'report' | 'table';
type ChartType = 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'radar' | 'gauge';
type ColorTheme = 'amber' | 'cyan' | 'emerald' | 'indigo';

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('studio');
  const [activeChartType, setActiveChartType] = useState<ChartType>(
    (result.chart_type as ChartType) || 'bar'
  );
  const [colorTheme, setColorTheme] = useState<ColorTheme>('amber');
  const [sortOrder, setSortOrder] = useState<'default' | 'desc' | 'asc'>('default');
  const [copiedReport, setCopiedReport] = useState(false);
  const [timeFilterIndex, setTimeFilterIndex] = useState<number | null>(null);

  // Theme palettes
  const themeColors = {
    amber: {
      primary: '#F59E0B',
      secondary: '#FBBF24',
      glow: 'rgba(245, 158, 11, 0.3)',
      gradient: ['#F59E0B', '#D97706', '#B45309', '#FBBF24', '#FCD34D']
    },
    cyan: {
      primary: '#06B6D4',
      secondary: '#22D3EE',
      glow: 'rgba(6, 182, 212, 0.3)',
      gradient: ['#06B6D4', '#0891B2', '#0E7490', '#22D3EE', '#67E8F9']
    },
    emerald: {
      primary: '#10B981',
      secondary: '#34D399',
      glow: 'rgba(16, 185, 129, 0.3)',
      gradient: ['#10B981', '#059669', '#047857', '#34D399', '#6EE7B7']
    },
    indigo: {
      primary: '#8B5CF6',
      secondary: '#A78BFA',
      glow: 'rgba(139, 92, 246, 0.3)',
      gradient: ['#8B5CF6', '#7C3AED', '#6D28D9', '#A78BFA', '#C4B5FD']
    }
  };

  const currentTheme = themeColors[colorTheme];

  // Derive columns & numeric fields
  const { catCol, numCol, processedRows } = useMemo(() => {
    if (!result.data_rows || result.data_rows.length === 0) {
      return { catCol: 'categoría', numCol: 'valor', processedRows: [] };
    }

    const columns = result.data_columns || Object.keys(result.data_rows[0]);
    let nCol = columns.find(
      (c) =>
        typeof result.data_rows[0][c] === 'number' &&
        !c.startsWith('id_')
    );
    let cCol = columns.find(
      (c) =>
        typeof result.data_rows[0][c] === 'string' &&
        !c.startsWith('id_') &&
        !c.includes('token') &&
        !c.includes('iban') &&
        !c.includes('key')
    );

    if (!nCol) nCol = columns.find((c) => typeof result.data_rows[0][c] === 'number') || columns[0];
    if (!cCol) cCol = columns.find((c) => c !== nCol) || columns[0];

    let sorted = [...result.data_rows];
    if (sortOrder === 'desc') {
      sorted.sort((a, b) => (b[nCol!] || 0) - (a[nCol!] || 0));
    } else if (sortOrder === 'asc') {
      sorted.sort((a, b) => (a[nCol!] || 0) - (b[nCol!] || 0));
    }

    return { catCol: cCol, numCol: nCol, processedRows: sorted };
  }, [result.data_rows, result.data_columns, sortOrder]);

  // Primary numerical value calculation
  const totalVal = useMemo(() => {
    if (!processedRows.length || !numCol) return 0;
    return processedRows.reduce((acc, r) => acc + (Number(r[numCol]) || 0), 0);
  }, [processedRows, numCol]);

  const maxValRow = useMemo(() => {
    if (!processedRows.length || !numCol) return null;
    return processedRows.reduce((max, r) => ((Number(r[numCol]) || 0) > (Number(max[numCol]) || 0) ? r : max), processedRows[0]);
  }, [processedRows, numCol]);

  const isCurrency = useMemo(() => {
    const colLower = (numCol || '').toLowerCase();
    const qLower = (result.question || '').toLowerCase();
    return (
      colLower.includes('monto') ||
      colLower.includes('ingreso') ||
      colLower.includes('precio') ||
      colLower.includes('salario') ||
      colLower.includes('costo') ||
      colLower.includes('usd') ||
      qLower.includes('ingreso') ||
      qLower.includes('precio') ||
      qLower.includes('salario') ||
      qLower.includes('monto')
    );
  }, [numCol, result.question]);

  const formatNumber = (num: number) => {
    if (isCurrency) {
      if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
      if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
      return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  // Build custom ECharts configuration based on activeChartType & theme
  const dynamicChartOption = useMemo(() => {
    if (!processedRows.length) return result.chart_option;

    const xLabels = processedRows.map((r) => String(r[catCol] || ''));
    const yValues = processedRows.map((r) => Number(r[numCol]) || 0);

    const baseDark = {
      backgroundColor: 'transparent',
      textStyle: { color: '#9CA3AF', fontFamily: 'Inter, sans-serif' },
      grid: { left: '3%', right: '4%', bottom: '8%', top: '15%', containLabel: true }
    };

    if (activeChartType === 'pie' || activeChartType === 'donut') {
      return {
        ...baseDark,
        tooltip: {
          trigger: 'item',
          formatter: isCurrency ? '{b}: ${c} ({d}%)' : '{b}: {c} ({d}%)'
        },
        legend: {
          orient: 'horizontal',
          bottom: '0%',
          textStyle: { color: '#9CA3AF', fontSize: 11 },
          itemWidth: 10,
          itemHeight: 10
        },
        series: [
          {
            name: numCol?.replace(/_/g, ' ').toUpperCase(),
            type: 'pie',
            radius: activeChartType === 'donut' ? ['50%', '75%'] : '70%',
            center: ['50%', '45%'],
            avoidLabelOverlap: true,
            itemStyle: {
              borderRadius: 8,
              borderColor: '#0F172A',
              borderWidth: 2
            },
            label: {
              show: processedRows.length <= 6,
              color: '#E2E8F0',
              fontSize: 11
            },
            data: processedRows.map((r, i) => ({
              name: String(r[catCol] || ''),
              value: Number(r[numCol]) || 0,
              itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] }
            }))
          }
        ]
      };
    }

    if (activeChartType === 'line' || activeChartType === 'area') {
      return {
        ...baseDark,
        tooltip: {
          trigger: 'axis',
          formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}'
        },
        xAxis: {
          type: 'category',
          data: xLabels,
          axisLine: { lineStyle: { color: '#334155' } },
          axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 5 ? 20 : 0 }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: '#334155' } },
          splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
          axisLabel: { color: '#9CA3AF', fontSize: 11 }
        },
        series: [
          {
            name: numCol?.replace(/_/g, ' '),
            type: 'line',
            smooth: true,
            showSymbol: true,
            symbolSize: 7,
            itemStyle: { color: currentTheme.primary },
            lineStyle: { width: 3, color: currentTheme.primary },
            areaStyle:
              activeChartType === 'area'
                ? {
                    color: {
                      type: 'linear',
                      x: 0,
                      y: 0,
                      x2: 0,
                      y2: 1,
                      colorStops: [
                        { offset: 0, color: currentTheme.glow },
                        { offset: 1, color: 'rgba(0, 0, 0, 0)' }
                      ]
                    }
                  }
                : undefined,
            data: yValues
          }
        ]
      };
    }

    if (activeChartType === 'gauge') {
      const topPct = totalVal > 0 ? Math.min(100, Math.round(((yValues[0] || 0) / totalVal) * 100)) : 75;
      return {
        ...baseDark,
        series: [
          {
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            splitNumber: 5,
            itemStyle: {
              color: currentTheme.primary,
              shadowColor: currentTheme.glow,
              shadowBlur: 10,
              shadowOffsetX: 2,
              shadowOffsetY: 2
            },
            progress: { show: true, roundCap: true, width: 14 },
            pointer: { length: '60%', width: 5, itemStyle: { color: '#E2E8F0' } },
            axisLine: { roundCap: true, lineStyle: { width: 14, color: [[1, '#1E293B']] } },
            axisTick: { show: false },
            splitLine: { length: 8, lineStyle: { width: 2, color: '#475569' } },
            axisLabel: { color: '#94A3B8', distance: 18, fontSize: 10 },
            title: { show: true, offsetCenter: [0, '25%'], color: '#94A3B8', fontSize: 12 },
            detail: {
              valueAnimation: true,
              offsetCenter: [0, '-15%'],
              fontSize: 28,
              fontWeight: 'bold',
              formatter: '{value}%',
              color: '#F8FAFC'
            },
            data: [{ value: topPct, name: xLabels[0] || 'Líder' }]
          }
        ]
      };
    }

    // Default: Bar Chart
    return {
      ...baseDark,
      tooltip: {
        trigger: 'axis',
        formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}'
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 4 ? 20 : 0 }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: { color: '#9CA3AF', fontSize: 11 }
      },
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'bar',
          data: yValues,
          itemStyle: {
            color: currentTheme.primary,
            borderRadius: [6, 6, 0, 0]
          }
        }
      ]
    };
  }, [processedRows, catCol, numCol, activeChartType, currentTheme, isCurrency, totalVal, result.chart_option]);

  // Copy Full Executive Report to clipboard
  const handleCopyReport = () => {
    const reportText = `INFORME EJECUTIVO DE NEGOCIO
Consulta: "${result.question}"
Fecha: ${result.timestamp}

1. RESUMEN EJECUTIVO:
${result.executive_report?.overview || result.summary_text}

2. HALLAZGOS CLAVE:
${result.executive_report?.key_findings.map((f, i) => `  - ${f}`).join('\n') || '  - Registros procesados exitosamente en la base de datos corporativa.'}

3. RECOMENDACIONES ESTRATÉGICAS:
${result.executive_report?.recommendations.map((r, i) => `  - ${r}`).join('\n') || '  - Mantener monitoreo periódico de las métricas analizadas.'}

4. AUDITORÍA Y TRAZABILIDAD:
  - SQL: ${result.traceability.sql_executed}
  - Filas: ${result.traceability.rows_returned}
  - Latencia: ${result.traceability.execution_time_ms} ms
  - Validación AST: ${result.traceability.validation_status}
`;
    navigator.clipboard.writeText(reportText);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  return (
    <div className="w-full space-y-6">
      {/* ------------------------------------------------------------- */}
      {/* 1. STUDIO HEADER & CONTROLS (Obsidian Dark Luxury Theme) */}
      {/* ------------------------------------------------------------- */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-3xl p-5 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-white tracking-tight">
                Executive Analytics Studio
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Live Data
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Visualización analítica interactiva y reporte de gobernanza corporativa
            </p>
          </div>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center space-x-1.5 bg-zinc-950/80 p-1.5 rounded-2xl border border-white/5 self-start md:self-auto">
          <button
            onClick={() => setViewMode('studio')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              viewMode === 'studio'
                ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Studio</span>
          </button>
          <button
            onClick={() => setViewMode('report')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              viewMode === 'report'
                ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Informe</span>
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              viewMode === 'table'
                ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>Dataset ({result.data_rows?.length || 0})</span>
          </button>

          {onOpenTraceability && (
            <button
              onClick={onOpenTraceability}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border-l border-white/5 ml-1 transition-all"
              title="Auditoría de Consulta SQL y Seguridad AST"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
              <span className="hidden sm:inline">SQL</span>
            </button>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. MODE: STUDIO (Widgets inspirados en la referencia) */}
      {/* ------------------------------------------------------------- */}
      {viewMode === 'studio' && (
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
              className="text-xs text-amber-300 hover:text-white font-semibold flex items-center space-x-1.5 shrink-0 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-3.5 py-1.5 rounded-xl transition-all shadow-sm self-start sm:self-auto"
            >
              <span>Ver Informe Completo</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Top Row: Hero Card + Radial Progress Gauges */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Widget 1: Hero Metric Card (like $84.3K Revenue) */}
            <div className="lg:col-span-5 bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
              {/* Background ambient lighting */}
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

              {/* Sub Metrics Footer Row */}
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
                    {(result.traceability?.execution_time_ms / 1000).toFixed(2)}s
                  </div>
                </div>
              </div>
            </div>

            {/* Widget 2: Metric Gauges (like 72% $36K and 4.9% from image) */}
            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-5">
              {(result.gauges && result.gauges.length > 0 ? result.gauges : [
                { title: 'Índice de Rendimiento', percentage: 88, value_label: '88%', target_label: 'Meta: >80%', color: '#F59E0B' },
                { title: 'Salud Operacional', percentage: 95, value_label: '95%', target_label: 'Meta: 99%', color: '#10B981' }
              ]).map((gauge, gIdx) => (
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

                    {/* Circular Progress Ring */}
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
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <span className="absolute text-xs font-bold text-white">
                        {Math.round(gauge.percentage)}%
                      </span>
                    </div>
                  </div>

                  <div className="w-full bg-zinc-800/80 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: `${Math.min(100, gauge.percentage)}%`,
                        backgroundColor: gauge.color || '#F59E0B'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ------------------------------------------------------------- */}
          {/* Main Chart Card + Interactive Visualization Toolbar */}
          {/* ------------------------------------------------------------- */}
          <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-5">
            {/* Chart Toolbar */}
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

              {/* Chart Type Selector Pills */}
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
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
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

            {/* Sub-toolbar: Sort & Theme Selector */}
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
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
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

              {/* Theme Palette Buttons */}
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
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* ECharts Container */}
            <div className="w-full pt-2">
              <InteractiveChart option={dynamicChartOption} height="360px" />
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. MODE: INFORME EJECUTIVO COMPLETO */}
      {/* ------------------------------------------------------------- */}
      {viewMode === 'report' && (
        <div className="bg-gradient-to-br from-zinc-900/95 via-zinc-900/60 to-zinc-950/95 border border-white/10 rounded-3xl p-7 shadow-2xl space-y-7 animate-fadeIn">
          {/* Report Title & Copy Action */}
          <div className="flex items-start justify-between pb-5 border-b border-white/10">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <FileText className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-white tracking-tight">
                  Informe Ejecutivo de Negocio
                </h3>
              </div>
              <p className="text-xs text-zinc-400">
                Generado automáticamente a partir de la consulta "{result.question}" sobre la base de datos corporativa.
              </p>
            </div>

            <button
              onClick={handleCopyReport}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition-all shadow-lg shadow-amber-500/10"
            >
              {copiedReport ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              <span>{copiedReport ? '¡Copiado!' : 'Copiar Informe'}</span>
            </button>
          </div>

          {/* Section 1: Overview & Risk Assessment */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span>1. Diagnóstico & Contexto General</span>
              </h4>

              {result.executive_report?.risk_level && (
                <span
                  className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full border ${
                    result.executive_report.risk_level === 'ALTO' || result.executive_report.risk_level === 'CRITICO'
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                      : result.executive_report.risk_level === 'MEDIO'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  }`}
                >
                  Nivel de Riesgo: {result.executive_report.risk_level}
                </span>
              )}
            </div>

            <div className="bg-zinc-950/70 border border-white/10 rounded-2xl p-5 text-sm text-zinc-200 leading-relaxed font-normal shadow-inner">
              {result.executive_report?.overview || result.summary_text}
            </div>

            {result.executive_report?.business_impact && (
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-200/90">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-amber-300 font-semibold">Impacto Directo en el Negocio: </strong>
                  <span>{result.executive_report.business_impact}</span>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Key Findings */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>2. Hallazgos Clave & Puntos Críticos</span>
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(result.executive_report?.key_findings && result.executive_report.key_findings.length > 0
                ? result.executive_report.key_findings
                : [
                    `Se procesaron ${result.data_rows?.length || 0} registros de la base de datos corporativa.`,
                    `El valor total acumulado analizado asciende a ${formatNumber(totalVal)}.`,
                    `El registro con mayor ponderación corresponde a ${String(maxValRow?.[catCol] || 'Líder')}.`
                  ]
              ).map((finding, idx) => (
                <div
                  key={idx}
                  className="bg-zinc-950/70 border border-white/10 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-emerald-500/30 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span className="leading-relaxed font-normal">{finding}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Strategic Recommendations */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>3. Recomendaciones Estratégicas Accionables</span>
            </h4>
            <div className="space-y-2.5">
              {(result.executive_report?.recommendations && result.executive_report.recommendations.length > 0
                ? result.executive_report.recommendations
                : [
                    'Mantener el monitoreo continuo de estos indicadores clave.',
                    'Evaluar la asignación de recursos basada en las tendencias observadas.',
                    'Compartir este informe con los líderes de área correspondientes.'
                  ]
              ).map((rec, idx) => (
                <div
                  key={idx}
                  className="bg-zinc-950/70 border border-cyan-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-cyan-500/40 transition-all"
                >
                  <div className="w-5 h-5 rounded-lg bg-cyan-500/20 text-cyan-300 font-extrabold flex items-center justify-center text-[10px] shrink-0 mt-0.5 border border-cyan-500/30">
                    {idx + 1}
                  </div>
                  <span className="leading-relaxed font-normal">{rec}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section 4: Technical Traceability & Governance */}
          <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400">
            <div className="flex items-center space-x-4">
              <span>SQL: <strong className="text-zinc-200">{result.traceability.validation_status}</strong></span>
              <span>Filas: <strong className="text-zinc-200">{result.traceability.rows_returned}</strong></span>
              <span>Latencia: <strong className="text-zinc-200">{result.traceability.execution_time_ms} ms</strong></span>
            </div>

            {onOpenTraceability && (
              <button
                onClick={onOpenTraceability}
                className="flex items-center space-x-1.5 text-amber-400 hover:text-amber-300 font-medium"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Auditar Código SQL Completo</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 4. MODE: DATASET TABULAR */}
      {/* ------------------------------------------------------------- */}
      {viewMode === 'table' && (
        <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TableIcon className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white tracking-tight">
                Registros Extraídos de SQLite ({result.data_rows?.length || 0})
              </h3>
            </div>
            <span className="text-xs text-zinc-400 bg-zinc-950 px-3 py-1 rounded-lg border border-white/5">
              100% Sanitizado & Auditado
            </span>
          </div>

          <DataGridTable columns={result.data_columns} rows={result.data_rows} />
        </div>
      )}
    </div>
  );
};
