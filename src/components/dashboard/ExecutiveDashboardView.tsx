import React, { useState, useMemo } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import { ExecutiveReportView } from './ExecutiveReportView';
import { ExecutiveStudioView, ChartType } from './ExecutiveStudioView';
import { THEME_COLORS, deriveProcessedRows, formatMetricNumber } from './executiveDashboardUtils';
import { BarChart3, FileText, Table as TableIcon, ShieldCheck, Sparkles } from 'lucide-react';

interface ExecutiveDashboardViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
}

type ViewMode = 'studio' | 'report' | 'table';
type ColorTheme = 'amber' | 'cyan' | 'emerald' | 'indigo';

export const ExecutiveDashboardView: React.FC<ExecutiveDashboardViewProps> = ({
  result,
  onOpenTraceability
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('studio');
  const [activeChartType, setActiveChartType] = useState<ChartType>(
    (result.chart_type as ChartType) || 'bar'
  );
  const [colorTheme, setColorTheme] = useState<ColorTheme>('amber');
  const [sortOrder, setSortOrder] = useState<'default' | 'desc' | 'asc'>('default');
  const [copiedReport, setCopiedReport] = useState(false);

  const currentTheme = THEME_COLORS[colorTheme];

  const { catCol, numCol, processedRows } = useMemo(
    () => deriveProcessedRows(result, sortOrder),
    [result, sortOrder]
  );

  const totalVal = useMemo(() => {
    if (!processedRows.length || !numCol) return 0;
    return processedRows.reduce((acc, r) => acc + (Number(r[numCol]) || 0), 0);
  }, [processedRows, numCol]);

  const maxValRow = useMemo(() => {
    if (!processedRows.length || !numCol) return null;
    return processedRows.reduce((max, r) => ((Number(r[numCol]) || 0) > (Number(max[numCol]) || 0) ? r : max), processedRows[0]);
  }, [processedRows, numCol]);

  const isCurrency = useMemo(() => {
    const colLower = (numCol || '').toLowerCase();
    const qLower = (result.question || '').toLowerCase();
    return (
      colLower.includes('monto') ||
      colLower.includes('ingreso') ||
      colLower.includes('precio') ||
      colLower.includes('salario') ||
      colLower.includes('costo') ||
      colLower.includes('usd') ||
      qLower.includes('ingreso') ||
      qLower.includes('precio') ||
      qLower.includes('salario') ||
      qLower.includes('monto')
    );
  }, [numCol, result.question]);

  const formatNumber = (num: number) => formatMetricNumber(num, isCurrency);

  const dynamicChartOption = useMemo(() => {
    if (!processedRows.length) return result.chart_option;

    const xLabels = processedRows.map((r) => String(r[catCol] || ''));
    const yValues = processedRows.map((r) => Number(r[numCol]) || 0);

    const baseDark = {
      backgroundColor: 'transparent',
      textStyle: { color: '#9CA3AF', fontFamily: 'Inter, sans-serif' },
      grid: { left: '3%', right: '4%', bottom: '8%', top: '15%', containLabel: true }
    };

    if (activeChartType === 'pie' || activeChartType === 'donut') {
      return {
        ...baseDark,
        tooltip: { trigger: 'item', formatter: isCurrency ? '{b}: ${c} ({d}%)' : '{b}: {c} ({d}%)' },
        legend: { orient: 'horizontal', bottom: '0%', textStyle: { color: '#9CA3AF', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
        series: [
          {
            name: numCol?.replace(/_/g, ' ').toUpperCase(),
            type: 'pie',
            radius: activeChartType === 'donut' ? ['50%', '75%'] : '70%',
            center: ['50%', '45%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 8, borderColor: '#0F172A', borderWidth: 2 },
            label: { show: processedRows.length <= 6, color: '#E2E8F0', fontSize: 11 },
            data: processedRows.map((r, i) => ({
              name: String(r[catCol] || ''),
              value: Number(r[numCol]) || 0,
              itemStyle: { color: currentTheme.gradient[i % currentTheme.gradient.length] }
            }))
          }
        ]
      };
    }

    if (activeChartType === 'line' || activeChartType === 'area') {
      return {
        ...baseDark,
        tooltip: { trigger: 'axis', formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}' },
        xAxis: { type: 'category', data: xLabels, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 5 ? 20 : 0 } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }, axisLabel: { color: '#9CA3AF', fontSize: 11 } },
        series: [
          {
            name: numCol?.replace(/_/g, ' '),
            type: 'line',
            smooth: true,
            showSymbol: true,
            symbolSize: 7,
            itemStyle: { color: currentTheme.primary },
            lineStyle: { width: 3, color: currentTheme.primary },
            areaStyle: activeChartType === 'area' ? { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: currentTheme.glow }, { offset: 1, color: 'rgba(0, 0, 0, 0)' }] } } : undefined,
            data: yValues
          }
        ]
      };
    }

    if (activeChartType === 'gauge') {
      const topPct = totalVal > 0 ? Math.min(100, Math.round(((yValues[0] || 0) / totalVal) * 100)) : 75;
      return {
        ...baseDark,
        series: [
          {
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 100,
            splitNumber: 5,
            itemStyle: { color: currentTheme.primary, shadowColor: currentTheme.glow, shadowBlur: 10, shadowOffsetX: 2, shadowOffsetY: 2 },
            progress: { show: true, roundCap: true, width: 14 },
            pointer: { length: '60%', width: 5, itemStyle: { color: '#E2E8F0' } },
            axisLine: { roundCap: true, lineStyle: { width: 14, color: [[1, '#1E293B']] } },
            axisTick: { show: false },
            splitLine: { length: 8, lineStyle: { width: 2, color: '#475569' } },
            axisLabel: { color: '#94A3B8', distance: 18, fontSize: 10 },
            title: { show: true, offsetCenter: [0, '25%'], color: '#94A3B8', fontSize: 12 },
            detail: { valueAnimation: true, offsetCenter: [0, '-15%'], fontSize: 28, fontWeight: 'bold', formatter: '{value}%', color: '#F8FAFC' },
            data: [{ value: topPct, name: xLabels[0] || 'Líder' }]
          }
        ]
      };
    }

    return {
      ...baseDark,
      tooltip: { trigger: 'axis', formatter: isCurrency ? '{b}: ${c}' : '{b}: {c}' },
      xAxis: { type: 'category', data: xLabels, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#9CA3AF', fontSize: 11, rotate: xLabels.length > 4 ? 20 : 0 } },
      yAxis: { type: 'value', axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }, axisLabel: { color: '#9CA3AF', fontSize: 11 } },
      series: [{ name: numCol?.replace(/_/g, ' '), type: 'bar', data: yValues, itemStyle: { color: currentTheme.primary, borderRadius: [6, 6, 0, 0] } }]
    };
  }, [processedRows, catCol, numCol, activeChartType, currentTheme, isCurrency, totalVal, result.chart_option]);

  const handleCopyReport = () => {
    const reportText = `INFORME EJECUTIVO DE NEGOCIO\nConsulta: "${result.question}"\nFecha: ${result.timestamp}\n\n1. RESUMEN EJECUTIVO:\n${result.executive_report?.overview || result.summary_text}\n\n2. HALLAZGOS CLAVE:\n${result.executive_report?.key_findings.map((f) => `  - ${f}`).join('\n') || '  - Registros procesados exitosamente.'}\n\n3. RECOMENDACIONES ESTRATÉGICAS:\n${result.executive_report?.recommendations.map((r) => `  - ${r}`).join('\n') || '  - Mantener monitoreo periódico.'}\n\n4. AUDITORÍA:\n  - SQL: ${result.traceability.sql_executed}\n  - Filas: ${result.traceability.rows_returned}\n  - Latencia: ${result.traceability.execution_time_ms} ms\n`;
    navigator.clipboard.writeText(reportText);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  return (
    <div className="w-full space-y-6">
      {/* Studio Header & View Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-3xl p-5 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-white tracking-tight">Executive Analytics Studio</h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Live Data</span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">Visualización analítica interactiva y reporte de gobernanza corporativa</p>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 bg-zinc-950/80 p-1.5 rounded-2xl border border-white/5 self-start md:self-auto">
          <button onClick={() => setViewMode('studio')} className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${viewMode === 'studio' ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold' : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'}`}>
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Studio</span>
          </button>
          <button onClick={() => setViewMode('report')} className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${viewMode === 'report' ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold' : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'}`}>
            <FileText className="w-3.5 h-3.5" />
            <span>Informe</span>
          </button>
          <button onClick={() => setViewMode('table')} className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${viewMode === 'table' ? 'bg-amber-500 text-zinc-950 shadow-lg shadow-amber-500/25 font-bold' : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'}`}>
            <TableIcon className="w-3.5 h-3.5" />
            <span>Dataset ({result.data_rows?.length || 0})</span>
          </button>

          {onOpenTraceability && (
            <button onClick={onOpenTraceability} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border-l border-white/5 ml-1 transition-colors" title="Auditoría de Consulta SQL y Seguridad AST">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
              <span className="hidden sm:inline">SQL</span>
            </button>
          )}
        </div>
      </div>

      {/* Mode Renderers */}
      {viewMode === 'studio' && (
        <ExecutiveStudioView
          result={result}
          totalVal={totalVal}
          maxValRow={maxValRow}
          numCol={numCol}
          catCol={catCol}
          currentTheme={currentTheme}
          activeChartType={activeChartType}
          setActiveChartType={setActiveChartType}
          sortOrder={sortOrder}
          setSortOrder={setSortOrder}
          colorTheme={colorTheme}
          setColorTheme={setColorTheme}
          dynamicChartOption={dynamicChartOption}
          formatNumber={formatNumber}
          setViewMode={setViewMode}
        />
      )}

      {viewMode === 'report' && (
        <ExecutiveReportView
          result={result}
          formatNumber={formatNumber}
          totalVal={totalVal}
          maxValRow={maxValRow}
          catCol={catCol}
          copiedReport={copiedReport}
          onCopyReport={handleCopyReport}
          onOpenTraceability={onOpenTraceability}
        />
      )}

      {viewMode === 'table' && (
        <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TableIcon className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white tracking-tight">Registros Extraídos de SQLite ({result.data_rows?.length || 0})</h3>
            </div>
            <span className="text-xs text-zinc-400 bg-zinc-950 px-3 py-1 rounded-lg border border-white/5">100% Sanitizado & Auditado</span>
          </div>
          <DataGridTable columns={result.data_columns} rows={result.data_rows} />
        </div>
      )}
    </div>
  );
};
