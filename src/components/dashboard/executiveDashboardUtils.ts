import { ChartType, THEME_COLORS, computeChartStats, deriveProcessedRows, formatMetricNumber } from '../../features/dashboard/components/charts/theme';
import { buildBarChartOption } from '../../features/dashboard/components/charts/barChartConfig';
import { buildPieChartOption } from '../../features/dashboard/components/charts/pieChartConfig';
import { buildLineChartOption } from '../../features/dashboard/components/charts/lineChartConfig';
import { buildGaugeChartOption } from '../../features/dashboard/components/charts/gaugeConfig';

export {
  THEME_COLORS,
  computeChartStats,
  deriveProcessedRows,
  formatMetricNumber,
  type ChartType,
  type ColorTheme,
  type ChartStats,
} from '../../features/dashboard/components/charts/theme';

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
  const { processedRows, activeChartType, fallbackChartOption } = params;

  if (!processedRows.length) return fallbackChartOption;

  if (activeChartType === 'pie' || activeChartType === 'donut') {
    return buildPieChartOption({ ...params, activeChartType });
  }

  if (activeChartType === 'bar' || activeChartType === 'horizontal_bar') {
    return buildBarChartOption({ ...params, activeChartType });
  }

  if (activeChartType === 'line' || activeChartType === 'area') {
    return buildLineChartOption({ ...params, activeChartType });
  }

  return buildGaugeChartOption(params);
}
