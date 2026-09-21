import React from 'react';
import { QueryResult } from '../../../types';
import { formatMetricNumber } from './charts/theme';

interface KPISectionProps {
  kpis?: QueryResult['kpis'];
}

export const KPISection: React.FC<KPISectionProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {kpis.map((kpi, idx) => {
          const isPositive = kpi.change_direction === 'positive';
          const isNegative = kpi.change_direction === 'negative';
          const rawVal = typeof kpi.value === 'number' ? kpi.value : parseFloat(String(kpi.value).replace(/[^0-9.-]+/g, ''));
          const displayVal = isNaN(rawVal) ? String(kpi.value) : formatMetricNumber(rawVal, String(kpi.value).includes('$'));

          return (
            <div
              key={kpi.title || idx}
              className="glass-card-interactive rounded-2xl p-4 shadow-lg flex flex-col justify-between group"
            >
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-600 dark:text-gray-300 uppercase tracking-wider">
                <span className="truncate">{kpi.title}</span>
                {kpi.change_direction && (
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                      isPositive
                        ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                        : isNegative
                        ? 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30'
                        : 'bg-slate-100 dark:bg-dark-base text-slate-700 dark:text-gray-400 border-slate-300 dark:border-dark-border'
                    }`}
                  >
                    {isPositive ? '↑ Elevado' : isNegative ? '↓ Reducido' : '• Estable'}
                  </span>
                )}
              </div>

              <div className="mt-2.5">
                <div className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight font-mono tabular-nums group-hover:scale-[1.01] transition-transform origin-left">
                  {displayVal}
                </div>
                {kpi.subtitle && (
                  <p className="text-[11px] text-slate-500 dark:text-gray-400 mt-1 truncate">
                    {kpi.subtitle}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
