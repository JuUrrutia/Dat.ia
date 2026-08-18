import { QueryResult } from '../../types';

export const THEME_COLORS = {
  amber: {
    primary: '#F59E0B',
    secondary: '#FBBF24',
    glow: 'rgba(245, 158, 11, 0.3)',
    gradient: ['#F59E0B', '#D97706', '#B45309', '#FBBF24', '#FDE68A']
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
    sorted.sort((a, b) => (b[nCol!] || 0) - (a[nCol!] || 0));
  } else if (sortOrder === 'asc') {
    sorted.sort((a, b) => (a[nCol!] || 0) - (b[nCol!] || 0));
  }

  return { catCol: cCol, numCol: nCol, processedRows: sorted };
}

export function formatMetricNumber(num: number, isCurrency: boolean): string {
  if (isCurrency) {
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
    return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toLocaleString();
}

export function buildDynamicChartOption(params: {
  processedRows: Record<string, any>[];
  catCol: string;
  numCol: string;
  activeChartType: string;
  currentTheme: (typeof THEME_COLORS)['amber'];
  isCurrency: boolean;
  totalVal: number;
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
    fallbackChartOption,
  } = params;

  if (!processedRows.length) return fallbackChartOption;

  const xLabels = processedRows.map((r) => String(r[catCol] || ''));
  const yValues = processedRows.map((r) => Number(r[numCol]) || 0);

  const baseDark = {
    backgroundColor: 'transparent',
    textStyle: { color: '#9CA3AF', fontFamily: 'Inter, sans-serif' },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '15%', containLabel: true },
  };

  if (activeChartType === 'pie' || activeChartType === 'donut') {
    return {
      ...baseDark,
      tooltip: { trigger: 'item', formatter: isCurrency ? '{b}: ${c} ({d}%)' : '{b}: {c} ({d}%)' },
      legend: { orient: 'horizontal', bottom: '0%', textStyle: { color: '#9CA3AF', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
      series: [
        {
          name: numCol?.replace(/_/g, ' ').toUpperCase(),
          type: 'pie',
          radius: activeChartType === 'donut' ? ['50%', '75%'] : '70%',
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 8, borderColor: '#0F172A', borderWidth: 2 },
          label: { show: processedRows.length <= 6, color: '#E2E8F0', fontSize: 11 },
          data: processedRows.map((r, i) => ({
            name: String(r[catCol] || ''),
            value: Number(r[numCol]) || 0,
            itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] },
          })),
        },
      ],
    };
  }

  if (activeChartType === 'line' || activeChartType === 'area') {
    return {
      ...baseDark,
      tooltip: { trigger: 'axis', formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}' },
      xAxis: { type: 'category', data: xLabels, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 5 ? 20 : 0 } },
      yAxis: { type: 'value', axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }, axisLabel: { color: '#9CA3AF', fontSize: 11 } },
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'line',
          smooth: true,
          showSymbol: true,
          symbolSize: 7,
          lineStyle: { width: 3, color: currentTheme.primary },
          itemStyle: { color: currentTheme.primary },
          areaStyle: activeChartType === 'area' ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: currentTheme.glow }, { offset: 1, color: 'rgba(0, 0, 0, 0)' }] } } : undefined,
          data: yValues,
        },
      ],
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
          itemStyle: { color: currentTheme.primary, shadowColor: currentTheme.glow, shadowBlur: 10, shadowOffsetX: 2, shadowOffsetY: 2 },
          progress: { show: true, roundCap: true, width: 14 },
          pointer: { length: '60%', width: 5, itemStyle: { color: '#E2E8F0' } },
          axisLine: { roundCap: true, lineStyle: { width: 14, color: [[1, '#1E293B']] } },
          axisTick: { show: false },
          splitLine: { length: 8, lineStyle: { width: 2, color: '#475569' } },
          axisLabel: { color: '#94A3B8', distance: 18, fontSize: 10 },
          title: { show: true, offsetCenter: [0, '25%'], color: '#94A3B8', fontSize: 12 },
          detail: { valueAnimation: true, offsetCenter: [0, '-15%'], fontSize: 28, fontWeight: 'bold', formatter: '{value}%', color: '#F8FAFC' },
          data: [{ value: topPct, name: xLabels[0] || 'Líder' }],
        },
      ],
    };
  }

  return {
    ...baseDark,
    tooltip: { trigger: 'axis', formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}' },
    xAxis: { type: 'category', data: xLabels, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 4 ? 20 : 0 } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }, axisLabel: { color: '#9CA3AF', fontSize: 11 } },
    series: [{ name: numCol?.replace(/_/g, ' '), type: 'bar', data: yValues, itemStyle: { color: currentTheme.primary, borderRadius: [6, 6, 0, 0] } }],
  };
}
