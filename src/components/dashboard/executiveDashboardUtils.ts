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
