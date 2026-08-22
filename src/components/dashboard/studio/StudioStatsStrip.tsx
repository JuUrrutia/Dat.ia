import React from 'react';
import { ChartStats } from '../executiveDashboardUtils';

interface StudioStatsStripProps {
  stats: ChartStats;
  formatNumber: (num: number) => string;
}

export const StudioStatsStrip: React.FC<StudioStatsStripProps> = ({ stats, formatNumber }) => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 p-3 rounded-2xl bg-zinc-950/60 border border-white/5">
      <div className="space-y-0.5">
        <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
          <span>Total</span>
        </div>
        <div className="text-xs sm:text-sm font-bold text-white font-mono truncate">
          {formatNumber(stats.total)}
        </div>
      </div>

      <div className="space-y-0.5">
        <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
          <span>Promedio</span>
        </div>
        <div className="text-xs sm:text-sm font-bold text-amber-400 font-mono truncate">
          {formatNumber(stats.avg)}
        </div>
      </div>

      <div className="space-y-0.5">
        <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
          <span>Máximo</span>
        </div>
        <div className="text-xs sm:text-sm font-bold text-emerald-400 font-mono truncate" title={stats.maxLabel}>
          {formatNumber(stats.max)}
        </div>
      </div>

      <div className="space-y-0.5">
        <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
          <span>Mínimo</span>
        </div>
        <div className="text-xs sm:text-sm font-bold text-rose-400 font-mono truncate" title={stats.minLabel}>
          {formatNumber(stats.min)}
        </div>
      </div>

      <div className="space-y-0.5 col-span-2 sm:col-span-1">
        <div className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1">
          <span>Muestras</span>
        </div>
        <div className="text-xs sm:text-sm font-bold text-cyan-400 font-mono truncate">
          {stats.count} registros
        </div>
      </div>
    </div>
  );
};
