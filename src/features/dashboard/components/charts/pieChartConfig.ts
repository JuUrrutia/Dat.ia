import { THEME_COLORS, computeChartStats, formatMetricNumber } from './theme';

export function buildPieChartOption(params: {
  processedRows: Record<string, any>[];
  catCol: string;
  numCol: string;
  activeChartType: 'pie' | 'donut';
  currentTheme: (typeof THEME_COLORS)['amber'];
  isCurrency: boolean;
  showDataLabels?: boolean;
}) {
  const {
    processedRows,
    catCol,
    numCol,
    activeChartType,
    currentTheme,
    isCurrency,
    showDataLabels = false,
  } = params;

  const stats = computeChartStats(processedRows, catCol, numCol);

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
    grid: { left: '3%', right: '4%', bottom: '10%', top: '12%', containLabel: true },
  };

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
