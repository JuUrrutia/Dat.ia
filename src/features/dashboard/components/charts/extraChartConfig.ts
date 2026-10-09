import { THEME_COLORS, computeChartStats, formatMetricNumber } from './theme';

type ExtraChartType = 'radial' | 'scatter' | 'gauge' | 'treemap';

export function buildExtraChartOption(params: {
  processedRows: Record<string, any>[];
  catCol: string;
  numCol: string;
  activeChartType: ExtraChartType;
  currentTheme: (typeof THEME_COLORS)['amber'];
  isCurrency: boolean;
  totalVal: number;
  showDataLabels?: boolean;
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
  } = params;

  const xLabels = processedRows.map((r) =>
    String(r[catCol] !== null && r[catCol] !== undefined ? r[catCol] : '')
  );
  const yValues = processedRows.map((r) => Number(r[numCol]) || 0);
  const stats = computeChartStats(processedRows, catCol, numCol);

  const baseTooltip = {
    backgroundColor: '#0F172A',
    borderColor: '#334155',
    borderWidth: 1,
    padding: [10, 14],
    textStyle: { color: '#F8FAFC', fontFamily: 'Inter, system-ui, sans-serif' },
    extraCssText:
      'box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7), 0 8px 10px -6px rgba(0, 0, 0, 0.7); border-radius: 12px; backdrop-filter: blur(8px);',
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

  const formatAxisLabel = (val: string) => {
    if (!val) return '';
    const str = String(val).trim();
    return str.length > 20 ? `${str.substring(0, 18)}...` : str;
  };

  if (activeChartType === 'radial') {
    // Categorías en el ángulo, magnitud en el radio: el ranking circular.
    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#94A3B8', fontFamily: 'Inter, system-ui, sans-serif' },
      tooltip: {
        ...baseTooltip,
        trigger: 'item',
        formatter: (p: any) => formatTooltipHtml(p.name, p.value),
      },
      angleAxis: {
        type: 'category',
        data: xLabels,
        startAngle: 90,
        axisLine: { lineStyle: { color: '#334155' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#CBD5E1',
          fontSize: 10,
          formatter: formatAxisLabel,
        },
      },
      radiusAxis: {
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: {
          color: '#94A3B8',
          fontSize: 9,
          formatter: (v: number) => formatMetricNumber(v, isCurrency),
        },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },
      },
      polar: { center: ['50%', '52%'], radius: '72%' },
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'bar',
          coordinateSystem: 'polar',
          roundCap: true,
          data: yValues.map((val, idx) => ({
            value: val,
            itemStyle: {
              color: currentTheme.gradient[idx % currentTheme.gradient.length],
            },
          })),
          label: {
            show: showDataLabels,
            position: 'middle',
            color: '#0B0F19',
            fontSize: 9,
            fontWeight: 'bold',
            formatter: (p: any) => formatMetricNumber(p.value, isCurrency),
          },
        },
      ],
    };
  }

  if (activeChartType === 'scatter') {
    // Una sola columna numérica: esto es un dot plot (x = índice), no un
    // scatter 2D. Sirve para ver distribución y outliers sin barras.
    const rotateAngle = xLabels.some((l) => l.length > 14) ? 25 : xLabels.length > 6 ? 15 : 0;
    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#94A3B8', fontFamily: 'Inter, system-ui, sans-serif' },
      grid: { left: '3%', right: '4%', bottom: '10%', top: '12%', containLabel: true },
      tooltip: {
        ...baseTooltip,
        trigger: 'item',
        formatter: (p: any) => formatTooltipHtml(xLabels[p.dataIndex] ?? '', p.value),
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        axisLine: { lineStyle: { color: '#334155' } },
        axisTick: { show: false },
        axisLabel: { color: '#94A3B8', fontSize: 10, rotate: rotateAngle, formatter: formatAxisLabel },
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
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'scatter',
          symbolSize: 14,
          data: yValues.map((val, idx) => ({
            value: val,
            itemStyle: {
              color: currentTheme.gradient[idx % currentTheme.gradient.length],
              borderColor: '#FFF',
              borderWidth: 1,
              shadowBlur: 8,
              shadowColor: currentTheme.glow,
            },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                yAxis: stats.avg,
                lineStyle: { color: currentTheme.secondary, type: 'dashed', width: 2 },
                label: {
                  show: true,
                  formatter: `Prom: ${formatMetricNumber(stats.avg, isCurrency)}`,
                  color: currentTheme.secondary,
                  fontSize: 10,
                  position: 'insideEndTop',
                },
              },
            ],
          },
        },
      ],
    };
  }

  if (activeChartType === 'gauge') {
    // Una sola cifra. Muestra el PROMEDIO contra el máximo: average <= max
    // siempre, así la aguja nunca pega al tope. Con totalVal contra max no
    // serviría — el total es la suma y siempre supera al máximo, la aguja
    // satura y el medidor deja de informar.
    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#94A3B8', fontFamily: 'Inter, system-ui, sans-serif' },
      tooltip: {
        ...baseTooltip,
        show: false,
      },
      series: [
        {
          name: numCol?.replace(/_/g, ' '),
          type: 'gauge',
          center: ['50%', '58%'],
          radius: '78%',
          min: 0,
          max: stats.max > 0 ? stats.max : 1,
          startAngle: 200,
          endAngle: -20,
          progress: {
            show: true,
            width: 14,
            roundCap: true,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: currentTheme.gradient[1] },
                  { offset: 1, color: currentTheme.primary },
                ],
              },
            },
          },
          axisLine: { lineStyle: { width: 14, color: [[1, 'rgba(255,255,255,0.06)']] } },
          pointer: { icon: 'path://M2,0 L-2,0 L0,-40 Z', length: '62%', width: 4, itemStyle: { color: currentTheme.secondary } },
          axisTick: { distance: -14, length: 4, lineStyle: { color: 'rgba(255,255,255,0.2)', width: 1 } },
          splitLine: { distance: -16, length: 8, lineStyle: { color: 'rgba(255,255,255,0.3)', width: 1.5 } },
          axisLabel: { distance: 14, color: '#64748B', fontSize: 9 },
          anchor: { show: false },
          title: { show: true, offsetCenter: [0, '32%'], color: '#94A3B8', fontSize: 11 },
          detail: {
            offsetCenter: [0, '2%'],
            color: currentTheme.primary,
            fontSize: 26,
            fontWeight: 'bold',
            fontFamily: 'monospace',
            formatter: (v: number) => formatMetricNumber(v, isCurrency),
          },
          data: [
            {
              value: stats.avg,
              name: `Promedio ${numCol ? numCol.replace(/_/g, ' ') : ''}`,
            },
          ],
        },
      ],
    };
  }

  // treemap: un solo nivel de jerarquía, el área es proporcional al valor.
  return {
    backgroundColor: 'transparent',
    textStyle: { color: '#94A3B8', fontFamily: 'Inter, system-ui, sans-serif' },
    tooltip: {
      ...baseTooltip,
      trigger: 'item',
      formatter: (p: any) => formatTooltipHtml(p.name, p.value),
    },
    series: [
      {
        name: numCol?.replace(/_/g, ' '),
        type: 'treemap',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        width: '96%',
        height: '92%',
        top: '2%',
        left: '2%',
        itemStyle: { borderColor: '#0B0F19', borderWidth: 2, gapWidth: 2 },
        label: {
          show: showDataLabels,
          color: '#F8FAFC',
          fontSize: 11,
          formatter: (p: any) => {
            const name = formatAxisLabel(p.name);
            return `${name}\n${formatMetricNumber(p.value, isCurrency)}`;
          },
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