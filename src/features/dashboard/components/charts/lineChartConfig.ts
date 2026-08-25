import { THEME_COLORS, computeChartStats, formatMetricNumber } from './theme';

export function buildLineChartOption(params: {
  processedRows: Record<string, any>[];
  catCol: string;
  numCol: string;
  activeChartType: 'line' | 'area';
  currentTheme: (typeof THEME_COLORS)['amber'];
  isCurrency: boolean;
  showDataLabels?: boolean;
  showAverageLine?: boolean;
  showDataZoom?: boolean;
}) {
  const {
    processedRows,
    catCol,
    numCol,
    activeChartType,
    currentTheme,
    isCurrency,
    showDataLabels = false,
    showAverageLine = true,
    showDataZoom = false,
  } = params;

  const xLabels = processedRows.map((r) => String(r[catCol] !== null && r[catCol] !== undefined ? r[catCol] : ''));
  const yValues = processedRows.map((r) => Number(r[numCol]) || 0);
  const stats = computeChartStats(processedRows, catCol, numCol);

  const formatAxisLabel = (val: string) => {
    if (!val) return '';
    const str = String(val).trim();
    return str.length > 20 ? `${str.substring(0, 18)}...` : str;
  };

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

  const rotateAngle = xLabels.some((l) => l.length > 14) ? 25 : xLabels.length > 6 ? 15 : 0;

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
