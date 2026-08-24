import React from 'react';
import { QueryResult } from '../../../types';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

interface ReportFindingsViewProps {
  result: QueryResult;
  formatNumber?: (num: number) => string;
  totalVal?: number;
  maxValRow?: Record<string, any> | null;
  catCol?: string;
}

export const ReportFindingsView: React.FC<ReportFindingsViewProps> = ({
  result,
}) => {
  const rowsCount = result.data_rows?.length || 0;
  const colsCount = result.data_columns?.length || 0;

  // Build clean fallback findings if not supplied by backend
  const fallbackFindings = [
    `Se procesaron ${rowsCount} registros de la base de datos activa para esta consulta.`,
    `Estructura organizada en ${colsCount} columnas de información disponible.`,
    result.kpis && result.kpis.length > 0 && result.kpis[0]?.value
      ? `Indicador principal: ${result.kpis[0].title} = ${result.kpis[0].value}.`
      : `Consulta ejecutada y validada con permisos de rol corporativo.`,
  ];

  const findings =
    result.executive_report?.key_findings && result.executive_report.key_findings.length > 0
      ? result.executive_report.key_findings
      : fallbackFindings;

  // Build clean fallback recommendations
  const fallbackRecommendations = [
    'Consultar la pestaña de Datos para inspeccionar los registros individuales en detalle.',
    'Aplicar filtros adicionales por periodo, categoría o dimensiones para segmentar la información.',
    'Cruzar estos resultados con métricas cuantitativas complementarias según sea necesario.',
  ];

  const recommendations =
    result.executive_report?.recommendations && result.executive_report.recommendations.length > 0
      ? result.executive_report.recommendations
      : fallbackRecommendations;

  return (
    <>
      {/* Section 1: Overview & Risk Assessment */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>1. Diagnóstico & Contexto General</span>
          </h4>

          {result.executive_report?.risk_level && (
            <span
              className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full border ${
                result.executive_report.risk_level === 'ALTO' || result.executive_report.risk_level === 'CRITICO'
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : result.executive_report.risk_level === 'MEDIO'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              }`}
            >
              Nivel de Riesgo: {result.executive_report.risk_level}
            </span>
          )}
        </div>

        <div className="bg-zinc-950/70 border border-white/10 rounded-2xl p-5 text-sm text-zinc-200 leading-relaxed font-normal shadow-inner whitespace-pre-line">
          {result.executive_report?.overview || result.summary_text}
        </div>

        {result.executive_report?.business_impact && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-200/90">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-amber-300 font-semibold">Impacto Directo en el Negocio: </strong>
              <span>{result.executive_report.business_impact}</span>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Key Findings */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>2. Hallazgos Clave & Puntos Críticos</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {findings.map((finding, idx) => (
            <div
              key={idx}
              className="bg-zinc-950/70 border border-white/10 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-emerald-500/30 transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed font-normal">{finding}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Strategic Recommendations */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>3. Recomendaciones Estratégicas Accionables</span>
        </h4>
        <div className="space-y-2.5">
          {recommendations.map((rec, idx) => (
            <div
              key={idx}
              className="bg-zinc-950/70 border border-cyan-500/20 rounded-2xl p-4 flex items-start space-x-3 text-xs text-zinc-200 shadow-md hover:border-cyan-500/40 transition-colors"
            >
              <div className="w-5 h-5 rounded-lg bg-cyan-500/20 text-cyan-300 font-extrabold flex items-center justify-center text-[10px] shrink-0 mt-0.5 border border-cyan-500/30">
                {idx + 1}
              </div>
              <span className="leading-relaxed font-normal">{rec}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};
