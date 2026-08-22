import { QueryResult } from '../../types';

export type ChartType =
  | 'bar'
  | 'horizontal_bar'
  | 'line'
  | 'area'
  | 'donut'
  | 'pie'
  | 'radar'
  | 'scatter'
  | 'funnel'
  | 'gauge'
  | 'treemap';

export type ColorTheme = 'amber' | 'cyan' | 'emerald' | 'indigo' | 'rose' | 'ocean' | 'rainbow';

export const THEME_COLORS: Record<
  ColorTheme,
  {
    primary: string;
    secondary: string;
    glow: string;
    gradient: string[];
    name: string;
  }
> = {
  amber: {
    name: 'Ámbar Ejecutivo',
    primary: '#F59E0B',
    secondary: '#FBBF24',
    glow: 'rgba(245, 158, 11, 0.35)',
    gradient: ['#F59E0B', '#D97706', '#B45309', '#FBBF24', '#FDE68A', '#78350F'],
  },
  cyan: {
    name: 'Cian Tecnológico',
    primary: '#06B6D4',
    secondary: '#22D3EE',
    glow: 'rgba(6, 182, 212, 0.35)',
    gradient: ['#06B6D4', '#0891B2', '#0E7490', '#22D3EE', '#67E8F9', '#155E75'],
  },
  emerald: {
    name: 'Esmeralda Financiero',
    primary: '#10B981',
    secondary: '#34D399',
    glow: 'rgba(16, 185, 129, 0.35)',
    gradient: ['#10B981', '#059669', '#047857', '#34D399', '#6EE7B7', '#064E3B'],
  },
  indigo: {
    name: 'Púrpura Datia IA',
    primary: '#8B5CF6',
    secondary: '#A78BFA',
    glow: 'rgba(139, 92, 246, 0.35)',
    gradient: ['#8B5CF6', '#7C3AED', '#6D28D9', '#A78BFA', '#C4B5FD', '#4C1D95'],
  },
  rose: {
    name: 'Rosa / Carmesí Neón',
    primary: '#F43F5E',
    secondary: '#FB7185',
    glow: 'rgba(244, 63, 94, 0.35)',
    gradient: ['#F43F5E', '#E11D48', '#BE123C', '#FB7185', '#FDA4AF', '#881337'],
  },
  ocean: {
    name: 'Azul Océano',
    primary: '#3B82F6',
    secondary: '#60A5FA',
    glow: 'rgba(59, 130, 246, 0.35)',
    gradient: ['#3B82F6', '#2563EB', '#1D4ED8', '#60A5FA', '#93C5FD', '#1E3A8A'],
  },
  rainbow: {
    name: 'Espectro Multicolor',
    primary: '#6366F1',
    secondary: '#EC4899',
    glow: 'rgba(99, 102, 241, 0.35)',
    gradient: ['#6366F1', '#EC4899', '#F59E0B', '#10B981', '#06B6D4', '#8B5CF6', '#F43F5E', '#14B8A6'],
  },
};

export interface ChartStats {
  total: number;
  avg: number;
  max: number;
  maxLabel: string;
  min: number;
  minLabel: string;
  count: number;
}

export function computeChartStats(
  rows: Record<string, any>[],
  catCol: string,
  numCol: string
): ChartStats {
  if (!rows.length || !numCol) {
    return { total: 0, avg: 0, max: 0, maxLabel: '-', min: 0, minLabel: '-', count: 0 };
  }

  let total = 0;
  let max = -Infinity;
  let maxLabel = '';
  let min = Infinity;
  let minLabel = '';

  for (const r of rows) {
    const val = Number(r[numCol]) || 0;
    const lbl = String(r[catCol] || '');
    total += val;
    if (val > max) {
      max = val;
      maxLabel = lbl;
    }
    if (val < min) {
      min = val;
      minLabel = lbl;
    }
  }

  const count = rows.length;
  const avg = count > 0 ? total / count : 0;

  return {
    total,
    avg,
    max: max === -Infinity ? 0 : max,
    maxLabel: maxLabel || '-',
    min: min === Infinity ? 0 : min,
    minLabel: minLabel || '-',
    count,
  };
}

export function deriveProcessedRows(
  result: QueryResult,
  sortOrder: 'default' | 'desc' | 'asc'
) {
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
    sorted.sort((a, b) => (Number(b[nCol!]) || 0) - (Number(a[nCol!]) || 0));
  } else if (sortOrder === 'asc') {
    sorted.sort((a, b) => (Number(a[nCol!]) || 0) - (Number(b[nCol!]) || 0));
  }

  return { catCol: cCol, numCol: nCol, processedRows: sorted };
}

export function formatMetricNumber(num: number, isCurrency: boolean): string {
  if (num === null || num === undefined || isNaN(num)) return '0';
  if (isCurrency) {
    if (Math.abs(num) >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
    if (Math.abs(num) >= 1_000) return `$${(num / 1_000).toFixed(1)}K`;
    return `$${num.toLocaleString('es-CL', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  }
  if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return Number.isInteger(num) ? num.toLocaleString('es-CL') : num.toFixed(2);
}

export function buildDynamicChartOption(params: {
  processedRows: Record<string, any>[];
  catCol: string;
  numCol: string;
  activeChartType: ChartType;
  currentTheme: (typeof THEME_COLORS)['amber'];
  isCurrency: boolean;
  totalVal: number;
  showDataLabels?: boolean;
  showAverageLine?: boolean;
  showDataZoom?: boolean;
  fallbackChartOption: any;
}) {
  const {
    processedRows,
    catCol,
    numCol,
    activeChartType,
    currentTheme,
    isCurrency,
    totalVal,
    showDataLabels = false,
    showAverageLine = true,
    showDataZoom = false,
    fallbackChartOption,
  } = params;

  if (!processedRows.length) return fallbackChartOption;

  const xLabels = processedRows.map((r) => String(r[catCol] !== null && r[catCol] !== undefined ? r[catCol] : ''));
  const yValues = processedRows.map((r) => Number(r[numCol]) || 0);
  const stats = computeChartStats(processedRows, catCol, numCol);

  const formatAxisLabel = (val: string) => {
    if (!val) return '';
    const str = String(val).trim();
    return str.length > 20 ? `${str.substring(0, 18)}...` : str;
  };

  // High-contrast, crystal-clear dark glassmorphism tooltip
  const baseTooltip = {
    backgroundColor: '#0F172A',
    borderColor: '#334155',
    borderWidth: 1,
    padding: [10, 14],
    textStyle: { color: '#F8FAFC', fontFamily: 'Inter, system-ui, sans-serif' },
    extraCssText: 'box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7), 0 8px 10px -6px rgba(0, 0, 0, 0.7); border-radius: 12px; backdrop-filter: blur(8px);',
  };

  const formatTooltipHtml = (name: string, val: number) => {
    const valStr = formatMetricNumber(val, isCurrency);
    const pctStr = stats.total > 0 ? `${((val / stats.total) * 100).toFixed(1)}%` : '';
    return `
      <div style="font-family:Inter,system-ui,sans-serif; min-width:140px; max-width:320px;">
        <div style="font-size:11px; font-weight:600; color:#94A3B8; margin-bottom:6px; word-wrap:break-word; line-height:1.3; border-bottom:1px solid #1E293B; padding-bottom:4px;">
          ${name}
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color:${currentTheme.primary};"></span>
            <span style="font-size:12px; font-weight:500; color:#E2E8F0;">${numCol?.replace(/_/g, ' ')}:</span>
          </div>
          <span style="font-size:13px; font-weight:700; color:${currentTheme.primary}; font-family:monospace;">${valStr}</span>
        </div>
        ${
          pctStr
            ? `<div style="font-size:10px; color:#64748B; margin-top:4px; text-align:right;">${pctStr} del total</div>`
            : ''
        }
      </div>
    `;
  };

  const baseDark = {
    backgroundColor: 'transparent',
    textStyle: { color: '#94A3B8', fontFamily: 'Inter, system-ui, sans-serif' },
    grid: { left: '3%', right: '4%', bottom: showDataZoom ? '18%' : '10%', top: '12%', containLabel: true },
  };

  const dataZoomComponent = showDataZoom || processedRows.length > 12
    ? [
        {
          type: 'slider',
          show: true,
          xAxisIndex: [0],
          bottom: '2%',
          height: 20,
          borderColor: '#334155',
          fillerColor: currentTheme.glow,
          textStyle: { color: '#94A3B8', fontSize: 10 },
          handleStyle: { color: currentTheme.primary, borderColor: '#fff' },
        },
      ]
    : undefined;

  const markLineConfig = showAverageLine && stats.count > 1
    ? {
        data: [
          {
            type: 'average',
            name: 'Promedio',
            lineStyle: { color: currentTheme.secondary, type: 'dashed', width: 2 },
            label: {
              show: true,
              formatter: (p: any) => `Prom: ${formatMetricNumber(p.value, isCurrency)}`,
              color: currentTheme.secondary,
              fontSize: 10,
              position: 'insideEndTop',
            },
          },
        ],
      }
    : undefined;

  // 1. DONUT & PIE CHARTS
  if (activeChartType === 'pie' || activeChartType === 'donut') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        trigger: 'item',
        formatter: (p: any) => formatTooltipHtml(p.name, p.value),
      },
      legend: {
        orient: 'horizontal',
        bottom: '0%',
        textStyle: { color: '#94A3B8', fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
        formatter: (name: string) => (name.length > 18 ? `${name.substring(0, 16)}...` : name),
      },
      series: [
        {
          name: numCol?.replace(/_/g, ' ').toUpperCase(),
          type: 'pie',
          radius: activeChartType === 'donut' ? ['45%', '72%'] : '68%',
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#0B0F19', borderWidth: 2 },
          label: {
            show: showDataLabels,
            formatter: '{b}: {d}%',
            color: '#E2E8F0',
            fontSize: 10,
          },
          emphasis: {
            label: { show: true, fontSize: 12, fontWeight: 'bold', color: '#FFF' },
            itemStyle: { shadowBlur: 15, shadowColor: 'rgba(0, 0, 0, 0.5)' },
          },
          data: processedRows.map((r, i) => ({
            name: String(r[catCol] || ''),
            value: Number(r[numCol]) || 0,
            itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] },
          })),
        },
      ],
    };
  }

  // 2. HORIZONTAL BAR (RANKING VIEW)
  if (activeChartType === 'horizontal_bar') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (p: any) => {
          const it = Array.isArray(p) ? p[0] : p;
          return formatTooltipHtml(it.name, it.value);
        },
      },
      xAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: {
          color: '#94A3B8',
          fontSize: 10,
          formatter: (v: number) => formatMetricNumber(v, isCurrency),
        },
      },
      yAxis: {
        type: 'category',
        data: xLabels,
        inverse: true, // Top ranked item on top
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: {
          color: '#CBD5E1',
          fontSize: 11,
          formatter: formatAxisLabel,
        },
      },
      dataZoom: dataZoomComponent,
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'bar',
          data: yValues.map((val, idx) => ({
            value: val,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: currentTheme.gradient[idx % currentTheme.gradient.length] },
                  { offset: 1, color: currentTheme.primary },
                ],
              },
              borderRadius: [0, 6, 6, 0],
            },
          })),
          label: {
            show: showDataLabels,
            position: 'right',
            color: '#F8FAFC',
            fontSize: 10,
            formatter: (p: any) => formatMetricNumber(p.value, isCurrency),
          },
          markLine: markLineConfig,
        },
      ],
    };
  }

  // 3. RADAR CHART
  if (activeChartType === 'radar') {
    const maxVal = stats.max > 0 ? stats.max * 1.15 : 100;
    const indicators = xLabels.slice(0, 10).map((lbl) => ({
      name: formatAxisLabel(lbl),
      max: maxVal,
    }));
    const radarData = yValues.slice(0, 10);

    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        trigger: 'item',
      },
      radar: {
        indicator: indicators,
        shape: 'polygon',
        splitNumber: 4,
        axisName: { color: '#CBD5E1', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(255, 255, 255, 0.02)', 'rgba(255, 255, 255, 0.05)'],
          },
        },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: radarData,
              name: numCol?.replace(/_/g, ' ').toUpperCase(),
              itemStyle: { color: currentTheme.primary },
              lineStyle: { width: 3, color: currentTheme.primary },
              areaStyle: { color: currentTheme.glow },
            },
          ],
        },
      ],
    };
  }

  // 4. FUNNEL CHART
  if (activeChartType === 'funnel') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        trigger: 'item',
        formatter: (p: any) => formatTooltipHtml(p.name, p.value),
      },
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'funnel',
          left: '10%',
          top: '10%',
          bottom: '10%',
          width: '80%',
          minSize: '10%',
          maxSize: '100%',
          sort: 'descending',
          gap: 4,
          label: {
            show: true,
            position: 'inside',
            formatter: (p: any) => `${formatAxisLabel(p.name)}: ${formatMetricNumber(p.value, isCurrency)}`,
            color: '#FFFFFF',
            fontSize: 11,
            fontWeight: 'bold',
          },
          itemStyle: { borderColor: '#0B0F19', borderWidth: 2 },
          data: processedRows.map((r, i) => ({
            name: String(r[catCol] || ''),
            value: Number(r[numCol]) || 0,
            itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] },
          })),
        },
      ],
    };
  }

  // 5. TREEMAP CHART
  if (activeChartType === 'treemap') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        formatter: (p: any) => formatTooltipHtml(p.name, p.value),
      },
      series: [
        {
          type: 'treemap',
          name: numCol?.replace(/_/g, ' '),
          roam: false,
          nodeClick: false,
          breadcrumb: { show: false },
          label: {
            show: true,
            formatter: (p: any) => `${p.name}\n${formatMetricNumber(p.value, isCurrency)}`,
            color: '#FFF',
            fontSize: 11,
            fontWeight: 'bold',
          },
          itemStyle: {
            borderColor: '#0B0F19',
            borderWidth: 2,
            gapWidth: 2,
          },
          data: processedRows.map((r, i) => ({
            name: String(r[catCol] || ''),
            value: Number(r[numCol]) || 0,
            itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] },
          })),
        },
      ],
    };
  }

  // 6. SCATTER CHART
  if (activeChartType === 'scatter') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        formatter: (p: any) => formatTooltipHtml(p.value[2] || p.name, p.value[1]),
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94A3B8', fontSize: 10, formatter: formatAxisLabel },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: { color: '#94A3B8', fontSize: 10, formatter: (v: number) => formatMetricNumber(v, isCurrency) },
      },
      dataZoom: dataZoomComponent,
      series: [
        {
          type: 'scatter',
          symbolSize: (data: any) => {
            const val = data[1];
            const max = stats.max || 1;
            return Math.max(14, Math.min(48, Math.round((val / max) * 45)));
          },
          data: yValues.map((v, i) => [i, v, xLabels[i]]),
          itemStyle: {
            color: currentTheme.primary,
            shadowBlur: 10,
            shadowColor: currentTheme.glow,
          },
          markLine: markLineConfig,
        },
      ],
    };
  }

  // 7. GAUGE CHART
  if (activeChartType === 'gauge') {
    const topPct = totalVal > 0 ? Math.min(100, Math.round(((yValues[0] || 0) / totalVal) * 100)) : 75;
    const gaugeName = xLabels[0] && xLabels[0].length > 22 ? `${xLabels[0].substring(0, 20)}...` : xLabels[0] || 'Líder';
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
            shadowBlur: 12,
            shadowOffsetX: 2,
            shadowOffsetY: 2,
          },
          progress: { show: true, roundCap: true, width: 16 },
          pointer: { length: '60%', width: 6, itemStyle: { color: '#E2E8F0' } },
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: 16,
              color: [
                [0.3, '#10B981'],
                [0.7, '#F59E0B'],
                [1, '#EF4444'],
              ],
            },
          },
          axisTick: { show: false },
          splitLine: { length: 8, lineStyle: { width: 2, color: '#475569' } },
          axisLabel: { color: '#94A3B8', distance: 20, fontSize: 10 },
          title: { show: true, offsetCenter: [0, '25%'], color: '#CBD5E1', fontSize: 12, fontWeight: 'bold' },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, '-15%'],
            fontSize: 28,
            fontWeight: 'bolder',
            formatter: '{value}%',
            color: '#F8FAFC',
          },
          data: [{ value: topPct, name: `${gaugeName} (${formatMetricNumber(yValues[0] || 0, isCurrency)})` }],
        },
      ],
    };
  }

  // 8. LINE & AREA CHARTS
  const rotateAngle = xLabels.some((l) => l.length > 14) ? 25 : xLabels.length > 6 ? 15 : 0;

  if (activeChartType === 'line' || activeChartType === 'area') {
    return {
      ...baseDark,
      tooltip: {
        ...baseTooltip,
        trigger: 'axis',
        formatter: (p: any) => {
          const it = Array.isArray(p) ? p[0] : p;
          return formatTooltipHtml(it.name, it.value);
        },
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: {
          color: '#94A3B8',
          fontSize: 10,
          rotate: rotateAngle,
          formatter: formatAxisLabel,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: {
          color: '#94A3B8',
          fontSize: 10,
          formatter: (v: number) => formatMetricNumber(v, isCurrency),
        },
      },
      dataZoom: dataZoomComponent,
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { width: 3.5, color: currentTheme.primary, shadowColor: currentTheme.glow, shadowBlur: 8 },
          itemStyle: { color: currentTheme.primary, borderColor: '#FFF', borderWidth: 1.5 },
          label: {
            show: showDataLabels,
            position: 'top',
            color: '#F8FAFC',
            fontSize: 10,
            formatter: (p: any) => formatMetricNumber(p.value, isCurrency),
          },
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
                      { offset: 1, color: 'rgba(0, 0, 0, 0)' },
                    ],
                  },
                }
              : undefined,
          data: yValues,
          markPoint: {
            data: [
              { type: 'max', name: 'Máximo', itemStyle: { color: '#10B981' } },
              { type: 'min', name: 'Mínimo', itemStyle: { color: '#EF4444' } },
            ],
          },
          markLine: markLineConfig,
        },
      ],
    };
  }

  // 9. DEFAULT: VERTICAL BAR CHART
  return {
    ...baseDark,
    tooltip: {
      ...baseTooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: any) => {
        const it = Array.isArray(p) ? p[0] : p;
        return formatTooltipHtml(it.name, it.value);
      },
    },
    xAxis: {
      type: 'category',
      data: xLabels,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#94A3B8',
        fontSize: 10,
        rotate: rotateAngle,
        formatter: formatAxisLabel,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#334155' } },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      axisLabel: {
        color: '#94A3B8',
        fontSize: 10,
        formatter: (v: number) => formatMetricNumber(v, isCurrency),
      },
    },
    dataZoom: dataZoomComponent,
    series: [
      {
        name: numCol?.replace(/_/g, ' '),
        type: 'bar',
        data: yValues.map((val, idx) => ({
          value: val,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: currentTheme.primary },
                { offset: 1, color: currentTheme.gradient[idx % currentTheme.gradient.length] },
              ],
            },
            borderRadius: [6, 6, 0, 0],
          },
        })),
        label: {
          show: showDataLabels,
          position: 'top',
          color: '#F8FAFC',
          fontSize: 10,
          formatter: (p: any) => formatMetricNumber(p.value, isCurrency),
        },
        markPoint: {
          data: [
            { type: 'max', name: 'Máximo', itemStyle: { color: '#10B981' } },
            { type: 'min', name: 'Mínimo', itemStyle: { color: '#EF4444' } },
          ],
        },
        markLine: markLineConfig,
      },
    ],
  };
}
