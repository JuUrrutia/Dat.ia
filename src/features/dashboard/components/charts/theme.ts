import { QueryResult } from '../../../../types';

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
