import React from 'react';
import { TrendingUp, ArrowUpRight } from 'lucide-react';
import { QueryResult } from '../../../types';

interface StudioHeroAndGaugesProps {
  result: QueryResult;
  totalVal: number;
  maxValRow: Record<string, any> | null;
  numCol: string;
  catCol: string;
  currentTheme: any;
  formatNumber: (num: number) => string;
}

export const StudioHeroAndGauges: React.FC<StudioHeroAndGaugesProps> = ({
  result,
  totalVal,
  maxValRow,
  numCol,
  catCol,
  currentTheme,
  formatNumber,
}) => {
  const hasGauges = Boolean(result.gauges && result.gauges.length > 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
      {/* Widget 1: Hero Metric Card */}
      <div
        className={`${
          hasGauges ? 'lg:col-span-5' : 'lg:col-span-12'
        } bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between`}
      >
        <div
          className="absolute -top-16 -right-16 w-48 h-48 rounded-full blur-3xl pointer-events-none opacity-20"
          style={{ backgroundColor: currentTheme.primary }}
        />

        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-zinc-400 mb-2">
            <span className="uppercase tracking-wider">Métrica Principal</span>
            <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md text-[11px]">
              <TrendingUp className="w-3 h-3" />
              <span>Óptimo</span>
            </span>
          </div>

          <div className="flex flex-wrap items-baseline gap-2 mt-1">
            <span className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              {formatNumber(totalVal || result.data_rows?.length || 0)}
            </span>
            <span className="text-xs text-zinc-400 font-medium">
              {numCol?.replace(/_/g, ' ') || 'total'}
            </span>
          </div>

          {maxValRow && (
            <div className="mt-3 flex items-center space-x-2 text-xs text-zinc-400 bg-zinc-950/50 border border-white/5 rounded-xl p-2.5">
              <ArrowUpRight className="w-4 h-4 text-amber-400 shrink-0" />
              <span className="truncate">
                Líder: <strong className="text-zinc-200">{String(maxValRow[catCol] || '')}</strong> (
                {formatNumber(Number(maxValRow[numCol]) || 0)})
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 pt-4 sm:pt-5 mt-4 sm:mt-5 border-t border-white/5">
          <div>
            <div className="text-[11px] text-zinc-400 font-medium">Registros Analizados</div>
            <div className="text-base sm:text-lg font-bold text-white mt-0.5">
              {result.data_rows?.length || 0} filas
            </div>
          </div>
          <div>
            <div className="text-[11px] text-zinc-400 font-medium">Latencia IA</div>
            <div className="text-base sm:text-lg font-bold text-emerald-400 mt-0.5">
              {(((result.traceability?.execution_time_ms ?? 0)) / 1000).toFixed(2)}s
            </div>
          </div>
        </div>
      </div>

      {/* Widget 2: Metric Gauges */}
      {hasGauges && (
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-5">
          {result.gauges!.map((gauge, gIdx) => (
            <div
              key={gIdx}
              className="bg-gradient-to-br from-zinc-900/80 via-zinc-900/40 to-zinc-950/80 border border-white/10 rounded-3xl p-6 shadow-2xl flex flex-col justify-between relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  {gauge.title}
                </span>
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: gauge.color || '#F59E0B' }} />
              </div>

              <div className="flex items-center justify-between my-4">
                <div>
                  <div className="text-3xl font-extrabold text-white tracking-tight">
                    {gauge.value_label}
                  </div>
                  <div className="text-xs text-zinc-400 mt-1 font-medium">
                    {gauge.target_label}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
