import React from 'react';
import ReactECharts from 'echarts-for-react';
import { QueryResult } from '../../../types';
import { THEME_COLORS, ColorTheme } from './charts/theme';
import { buildDynamicChartOption, deriveProcessedRows } from '../../../components/dashboard/executiveDashboardUtils';

interface ChartSectionProps {
  result: QueryResult;
  colorTheme?: ColorTheme;
  onThemeChange?: (theme: ColorTheme) => void;
}

export const ChartSection: React.FC<ChartSectionProps> = ({
  result,
  colorTheme = 'indigo',
  onThemeChange,
}) => {
  if (
    !result.chart_type ||
    result.chart_type === 'none' ||
    !result.chart_option ||
    !result.chart_option.series ||
    result.chart_option.series.length === 0
  ) {
    return null;
  }

  const currentTheme = THEME_COLORS[colorTheme] || THEME_COLORS.indigo;
  const { catCol, numCol, processedRows } = deriveProcessedRows(result, 'default');
  const isCurrency = Boolean(numCol && (numCol.includes('ingreso') || numCol.includes('monto') || numCol.includes('precio') || numCol.includes('costo') || numCol.includes('total')));
  const totalVal = processedRows.reduce((sum, r) => sum + (Number(r[numCol]) || 0), 0);

  const finalOption = buildDynamicChartOption({
    processedRows,
    catCol,
    numCol,
    activeChartType: result.chart_type as any,
    currentTheme,
    isCurrency,
    totalVal,
    fallbackChartOption: result.chart_option,
  });

  return (
    <div className="bg-zinc-900/90 border border-white/10 rounded-3xl p-6 shadow-2xl backdrop-blur-xl space-y-4">
      {/* Chart Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
            Visualización Analítica Proyectada
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Gráfico dinámico ({result.chart_type.toUpperCase()}) derivado del conjunto de datos en SQLite
          </p>
        </div>

        {/* Theme Selector */}
        {onThemeChange && (
          <div className="flex items-center space-x-1.5 bg-zinc-950 p-1 rounded-xl border border-white/10 self-start sm:self-auto">
            {(['indigo', 'cyan', 'emerald', 'amber', 'rose'] as ColorTheme[]).map((thm) => {
              const bgClass =
                thm === 'indigo'
                  ? 'bg-indigo-500'
                  : thm === 'cyan'
                  ? 'bg-cyan-400'
                  : thm === 'emerald'
                  ? 'bg-emerald-400'
                  : thm === 'amber'
                  ? 'bg-amber-400'
                  : 'bg-rose-500';

              return (
                <button
                  key={thm}
                  type="button"
                  onClick={() => onThemeChange(thm)}
                  aria-label={`Seleccionar tema ${thm}`}
                  className={`w-5 h-5 rounded-lg ${bgClass} transition-transform ${
                    colorTheme === thm ? 'scale-125 ring-2 ring-white' : 'opacity-60 hover:opacity-100'
                  }`}
                  title={`Tema ${thm.toUpperCase()}`}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* ECharts Canvas */}
      <div className="w-full h-80 sm:h-96">
        <ReactECharts
          option={finalOption}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </div>
    </div>
  );
};
