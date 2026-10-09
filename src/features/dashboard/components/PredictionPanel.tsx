import React, { useState } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  Users,
  Info,
  ChevronDown,
  ChevronRight,
  X,
  Check,
  AlertOctagon,
} from 'lucide-react';
import { PredictionResult, ForecastCard, RetentionReport } from '../../../types';
import { copyToClipboard } from '../../../shared/clipboard';

/**
 * Panel de predicciones.
 *
 * La regla de diseno de este componente es una sola: el limite de confianza se
 * muestra con el MISMO peso visual que el numero. Un forecast con +/-37% de
 * banda presentado en tipografia grande al lado de un punto unico se lee como una
 * certeza, y no lo es. Por eso la banda, el metodo y el numero de periodos van
 * siempre a la vista, no escondidos tras un "ver detalle".
 *
 * `prob: null` se pinta como "sin evidencia", nunca como 0%. Un 0% es una
 * afirmacion sobre el futuro; la ausencia de evidencia es otra cosa.
 */

interface PredictionPanelProps {
  prediction: PredictionResult | null;
  onClose: () => void;
  onAuditQuality?: () => void;
  loadingAudit?: boolean;
}

const money = (n: number | null | undefined): string =>
  n === null || n === undefined
    ? '—'
    : `$${Math.round(n).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;

const TIER_LABEL: Record<string, string> = {
  fiel: 'Fiel (3+ meses)',
  recurrente: 'Recurrente (2 meses)',
  unico: 'Compra única',
};

const TIER_STYLE: Record<string, string> = {
  fiel: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
  recurrente: 'bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
  unico: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
};

const SEVERITY_STYLE: Record<string, string> = {
  ALTO: 'border-red-300 bg-red-50 dark:border-red-800/60 dark:bg-red-950/40',
  MEDIO: 'border-amber-300 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/40',
  BAJO: 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/40',
};

function ProbPill({ prob, label = 'vuelve' }: { prob?: number | null; label?: string }) {
  if (prob === null || prob === undefined) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400"
        title={`Menos de 20 observaciones históricas: no hay base para publicar un porcentaje. ${label} no se puede afirmar.`}
      >
        <Info className="h-3 w-3" aria-hidden />
        sin evidencia
      </span>
    );
  }
  const tone =
    prob >= 50
      ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
      : prob >= 30
        ? 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
        : 'border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/60 dark:text-red-300';
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] font-semibold ${tone}`}>
      {prob.toFixed(1)}% {label}
    </span>
  );
}

function ForecastBlock({ forecast }: { forecast: ForecastCard }) {
  const [showSeries, setShowSeries] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!forecast.available) {
    return (
      <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/40">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" aria-hidden />
          Pronóstico no disponible
        </h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{forecast.reason}</p>
        {forecast.series?.length > 0 && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Serie disponible ({forecast.series.length} periodos):{' '}
            {forecast.series.map((r) => r.periodo).join(' · ')}
          </p>
        )}
      </section>
    );
  }

  const point = forecast.point ?? 0;
  const width = 100;
  const bandTop = ((forecast.upper ?? point) / (forecast.upper || 1)) * width;
  const bandBottom = ((forecast.lower ?? point) / (forecast.upper || 1)) * width;
  const pointPos = (point / (forecast.upper || 1)) * width;

  return (
    <section className="rounded-xl border border-brand-200 bg-white p-4 dark:border-brand-800/60 dark:bg-slate-900/60">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
            <TrendingUp className="h-4 w-4 text-brand-600 dark:text-brand-400" aria-hidden />
            Pronóstico para {forecast.period}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {forecast.table} · {forecast.metric_column}
            {forecast.income_only && ' · solo ingresos (montos positivos)'}
          </p>
        </div>
        {!forecast.reliable && (
          <span className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
            <ShieldAlert className="h-3 w-3" aria-hidden />
            Bajo conteo de evidencia
          </span>
        )}
      </header>

      {/* El punto y la banda con el mismo peso visual: esta es la informacion. */}
      <div className="mt-4 grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Estimación
          </p>
          <p className="mt-1 text-3xl font-bold tabular-nums text-slate-900 dark:text-slate-50">
            {money(point)}
          </p>
          <p className="mt-1 text-sm font-medium text-slate-600 dark:text-slate-300">
            Rango plausible {money(forecast.lower)} – {money(forecast.upper)}
          </p>
        </div>

        <div className="flex flex-col justify-center">
          <div className="relative h-3 rounded-full bg-slate-200 dark:bg-slate-700" aria-hidden>
            <div
              className="absolute inset-y-0 rounded-full bg-brand-400/70 dark:bg-brand-500/60"
              style={{ left: `${Math.max(0, bandBottom)}%`, width: `${Math.max(0, bandTop - bandBottom)}%` }}
            />
            <div
              className="absolute inset-y-0 w-0.5 bg-slate-900 dark:bg-slate-50"
              style={{ left: `${Math.min(width - 0.5, Math.max(0, pointPos))}%` }}
            />
          </div>
          <div className="mt-1 flex justify-between text-[11px] tabular-nums text-slate-500 dark:text-slate-400">
            <span>{money(forecast.lower)}</span>
            <span>{money(forecast.upper)}</span>
          </div>
        </div>
      </div>

      {/* La banda, el metodo y el tamaño de la muestra, siempre visibles. */}
      <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-200 pt-3 text-xs dark:border-slate-700 sm:grid-cols-4">
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Error histórico (MAPE)</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
            {forecast.mape?.toFixed(1)}%
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Ancho de banda</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
            ±{forecast.band_pct?.toFixed(1)}%
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Periodos / pruebas</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
            {forecast.n_periods} / {forecast.n_backtests}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Método</dt>
          <dd className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-100">
            {forecast.method}
          </dd>
        </div>
      </dl>

      {forecast.has_gaps && (
        <p className="mt-3 flex items-start gap-1.5 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
          La serie tiene periodos faltantes, así que el último valor no es realmente el anterior y el
          error medido puede no representar la serie completa.
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => setShowSeries((v) => !v)}
          className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline dark:text-brand-300"
          aria-expanded={showSeries}
        >
          {showSeries ? <ChevronDown className="h-3 w-3" aria-hidden /> : <ChevronRight className="h-3 w-3" aria-hidden />}
          {showSeries ? 'Ocultar' : 'Ver'} serie ({forecast.series?.length ?? 0} periodos)
        </button>
        {forecast.sql && (
          <button
            type="button"
            onClick={async () => {
              const ok = await copyToClipboard(forecast.sql!);
              if (ok) {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }
            }}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:underline dark:text-slate-300"
          >
            {copied ? <Check className="h-3 w-3" aria-hidden /> : null}
            {copied ? 'SQL copiado' : 'Copiar SQL'}
          </button>
        )}
      </div>

      {showSeries && (
        <table className="mt-3 w-full text-xs">
          <caption className="sr-only">Serie mensual que alimenta el pronóstico</caption>
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <th scope="col" className="py-1.5 font-medium">Periodo</th>
              <th scope="col" className="py-1.5 text-right font-medium">Valor</th>
            </tr>
          </thead>
          <tbody>
            {forecast.series.map((row, i) => (
              <tr key={i} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                <td className="py-1.5 tabular-nums text-slate-700 dark:text-slate-300">{row.periodo}</td>
                <td className="py-1.5 text-right tabular-nums text-slate-900 dark:text-slate-100">
                  {money(Number(row.valor))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function RetentionBlock({ retention }: { retention: RetentionReport }) {
  if (!retention.tiers?.length || !retention.top?.length) {
    return (
      <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/40">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
          <Users className="h-4 w-4 text-slate-500" aria-hidden />
          Retención no disponible
        </h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          {retention.reason ||
            'No se pudo medir la retención: la tabla no tiene una columna que identifique al cliente.'}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/60">
      <header>
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
          <Users className="h-4 w-4 text-brand-600 dark:text-brand-400" aria-hidden />
          Retención por cliente
        </h3>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
          {retention.total_clients} clientes · {money(retention.total_revenue)} · última observación {retention.last_period}
        </p>
      </header>

      <p className="mt-3 rounded-md bg-slate-50 p-2 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
        Cada probabilidad se cuenta sobre las transiciones reales de la serie (un cliente que compró y
        volvió al mes siguiente), clasificando cada cliente por los meses que llevaba activo{' '}
        <em>en ese momento</em>. No se usa información posterior.
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {retention.tiers.map((t) => (
          <div key={t.tier} className={`rounded-lg border p-2.5 ${TIER_STYLE[t.tier] ?? TIER_STYLE.unico}`}>
            <p className="text-[11px] font-medium uppercase tracking-wide opacity-80">
              {TIER_LABEL[t.tier] ?? t.tier}
            </p>
            <p className="mt-1 text-lg font-bold tabular-nums">
              {t.prob !== null && t.prob !== undefined ? `${t.prob.toFixed(1)}%` : 's/ev'}
            </p>
            <p className="mt-0.5 text-[11px] opacity-75 tabular-nums">
              {t.retornaron} de {t.casos} casos
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[540px] text-xs">
          <caption className="sr-only">Clientes ordenados por peso económico en riesgo</caption>
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <th scope="col" className="py-2 font-medium">Cliente</th>
              <th scope="col" className="py-2 font-medium">Segmento</th>
              <th scope="col" className="py-2 text-right font-medium">Ingreso</th>
              <th scope="col" className="py-2 text-right font-medium">% total</th>
              <th scope="col" className="py-2 font-medium">Última compra</th>
              <th scope="col" className="py-2 font-medium">Prob. de retorno</th>
            </tr>
          </thead>
          <tbody>
            {retention.top.map((c) => (
              <tr key={c.entity} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                <td className="max-w-[220px] truncate py-2 font-medium text-slate-800 dark:text-slate-200" title={c.entity}>
                  {c.entity}
                </td>
                <td className="py-2">
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${TIER_STYLE[c.tier] ?? TIER_STYLE.unico}`}>
                    {TIER_LABEL[c.tier] ?? c.tier}
                  </span>
                </td>
                <td className="py-2 text-right tabular-nums text-slate-700 dark:text-slate-300">{money(c.revenue)}</td>
                <td className="py-2 text-right tabular-nums text-slate-700 dark:text-slate-300">
                  {c.revenue_share.toFixed(2)}%
                </td>
                <td className="py-2 tabular-nums text-slate-600 dark:text-slate-400">
                  {c.last_purchase}
                  {c.months_since_last > 0 && (
                    <span className="ml-1 text-amber-700 dark:text-amber-400">(hace {c.months_since_last}m)</span>
                  )}
                </td>
                <td className="py-2">
                  <ProbPill prob={c.return_prob} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {retention.truncated_by_limit && (
          <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
            Se muestran los {retention.top.length} clientes de mayor peso en riesgo. Los porcentajes por
            segmento se calcularon sobre los {retention.total_clients} clientes completos.
          </p>
        )}
      </div>
    </section>
  );
}

export function PredictionPanel({ prediction, onClose, onAuditQuality, loadingAudit }: PredictionPanelProps) {
  if (!prediction) return null;

  const { forecast, retention, data_quality } = prediction;
  const errors = prediction.errors ?? [];
  const hasFindings = Array.isArray(data_quality) && data_quality.length > 0;

  return (
    <section
      aria-label="Predicciones"
      className="animate-slideUp space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/80"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-50">Predicciones</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Cálculo determinista sobre los datos reales. No interviene un modelo de lenguaje: cada
            número sale de la serie y cada límite viene medido.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar predicciones"
          className="rounded-md p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </header>

      {/* Fallo PARCIAL: se nombra en vez de dejar un hueco. Un bloque ausente
          sin explicar por que se lee igual que "no aplica". */}
      {errors.length > 0 && (
        <ul
          role="status"
          className="space-y-1 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200"
        >
          {errors.map((e, i) => (
            <li key={i}>No se pudo calcular — {e}</li>
          ))}
        </ul>
      )}

      {forecast && <ForecastBlock forecast={forecast} />}
      {retention && <RetentionBlock retention={retention} />}

      {/* Solo lectura: la auditoria NOMBRA los defectos, no corrige nada. */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900/60">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
            <AlertOctagon className="h-4 w-4 text-slate-500" aria-hidden />
            Calidad de los datos de origen
          </h3>
          {!hasFindings && onAuditQuality && (
            <button
              type="button"
              onClick={onAuditQuality}
              disabled={loadingAudit}
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {loadingAudit ? 'Analizando…' : 'Analizar'}
            </button>
          )}
        </div>

        {!onAuditQuality && !hasFindings && (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            No se ejecutó el análisis de calidad. Pídelo explícitamente: son consultas de conteo
            sobre toda la tabla.
          </p>
        )}

        {hasFindings && (
          <>
            <ul className="mt-3 space-y-2">
              {data_quality.map((f, i) => (
                <li key={`${f.check}-${i}`} className={`rounded-lg border p-2.5 ${SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.BAJO}`}>
                  <p className="text-xs font-semibold text-slate-800 dark:text-slate-100">
                    {f.check.replace(/_/g, ' ')}
                    {f.count !== null && f.count !== undefined && (
                      <span className="ml-1.5 font-normal tabular-nums opacity-75">({f.count})</span>
                    )}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-700 dark:text-slate-300">{f.detail}</p>
                </li>
              ))}
            </ul>
            <p className="mt-3 rounded-md bg-slate-50 p-2 text-[11px] text-slate-600 dark:bg-slate-800/60 dark:text-slate-400">
              Estos defectos sesgan cualquier proyección que se haga sobre la misma base. Esta pantalla
              los reporta y no modifica nada: la corrección le corresponde al dueño del dato.
            </p>
          </>
        )}
      </section>
    </section>
  );
}
