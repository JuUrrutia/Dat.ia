import { THEME_COLORS, computeChartStats, formatMetricNumber, ChartType } from './theme';

export function buildGaugeChartOption(params: {
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
}) {
  const {
    processedRows,
    catCol,
    numCol,
    activeChartType,
    currentTheme,
    isCurrency,
    totalVal,
    showDataZoom = false,
    showAverageLine = true,
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

  // DEFAULT GAUGE
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
