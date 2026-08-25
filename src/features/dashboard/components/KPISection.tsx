import React from 'react';
import { QueryResult } from '../../../types';
import { THEME_COLORS, formatMetricNumber } from './charts/theme';

interface KPISectionProps {
  kpis?: QueryResult['kpis'];
  gauges?: QueryResult['gauges'];
  colorTheme?: keyof typeof THEME_COLORS;
}

export const KPISection: React.FC<KPISectionProps> = ({
  kpis,
  gauges,
  colorTheme = 'indigo',
}) => {
  if ((!kpis || kpis.length === 0) && (!gauges || gauges.length === 0)) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* KPI Cards Grid */}
      {kpis && kpis.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {kpis.map((kpi, idx) => {
            const isPositive = kpi.change_direction === 'positive';
            const isNegative = kpi.change_direction === 'negative';
            const rawVal = typeof kpi.value === 'number' ? kpi.value : parseFloat(String(kpi.value).replace(/[^0-9.-]+/g, ''));
            const displayVal = isNaN(rawVal) ? String(kpi.value) : formatMetricNumber(rawVal, String(kpi.value).includes('$'));

            return (
              <div
                key={kpi.title || idx}
                className="bg-zinc-900/90 border border-white/10 rounded-2xl p-4 shadow-lg backdrop-blur-md flex flex-col justify-between hover:border-white/20 transition-all group"
              >
                <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                  <span className="truncate">{kpi.title}</span>
                  {kpi.change_direction && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        isPositive
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : isNegative
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}
                    >
                      {isPositive ? '↑ Elevado' : isNegative ? '↓ Reducido' : '• Estable'}
                    </span>
                  )}
                </div>

                <div className="mt-2.5">
                  <div className="text-2xl font-black text-white tracking-tight font-mono group-hover:scale-[1.02] transition-transform origin-left">
                    {displayVal}
                  </div>
                  {kpi.subtitle && (
                    <p className="text-[11px] text-zinc-400 mt-1 truncate">
                      {kpi.subtitle}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Gauges Grid */}
      {gauges && gauges.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {gauges.map((g, idx) => {
            const pct = Math.min(Math.max(g.percentage || 0, 0), 100);
            return (
              <div
                key={g.title || idx}
                className="bg-zinc-900/80 border border-white/10 rounded-2xl p-4 shadow-md backdrop-blur-sm space-y-3"
              >
                <div className="flex items-center justify-between text-xs font-bold text-white">
                  <span>{g.title}</span>
                  <span className="font-mono text-amber-400">{g.value_label || `${pct}%`}</span>
                </div>

                {/* Meter Progress Bar */}
                <div className="w-full bg-zinc-950 h-3.5 rounded-full overflow-hidden p-0.5 border border-white/5 relative">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 via-indigo-500 to-emerald-400 transition-all duration-700 shadow-sm"
                    style={{ width: `${pct}%` }}
                  />
                </div>

                {g.target_label && (
                  <div className="flex justify-end text-[10px] text-zinc-400 font-mono">
                    Meta: {g.target_label}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
