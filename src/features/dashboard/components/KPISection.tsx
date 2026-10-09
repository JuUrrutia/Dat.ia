import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Percent,
  Layers,
  Activity,
  DollarSign,
  Filter,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react';
import { QueryResult, KPICard } from '../../../types';
import { formatMetricNumber } from './charts/theme';
import { copyToClipboard } from '../../../shared/clipboard';

interface KPISectionProps {
  kpis?: QueryResult['kpis'];
}

type ArchetypeId = 'percentage' | 'currency' | 'density' | 'volume';

interface ArchetypeTheme {
  id: ArchetypeId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
  iconBg: string;
  iconColor: string;
  accentBorder: string;
  glowHover: string;
  tagBg: string;
  tagText: string;
  tagBorder: string;
  suffixColor: string;
}

const ARCHETYPE_THEMES: Record<ArchetypeId, ArchetypeTheme> = {
  percentage: {
    id: 'percentage',
    label: 'Proporción',
    icon: Percent,
    accentColor: '#8B5CF6',
    iconBg: 'bg-violet-500/10 dark:bg-violet-500/20',
    iconColor: 'text-violet-700 dark:text-violet-300',
    accentBorder: 'border-violet-500/30 dark:border-violet-500/40',
    glowHover: 'hover:border-violet-500/50 hover:shadow-[0_8px_25px_-4px_rgba(139,92,246,0.22)]',
    tagBg: 'bg-violet-50 dark:bg-violet-950/60',
    tagText: 'text-violet-700 dark:text-violet-300',
    tagBorder: 'border-violet-200 dark:border-violet-800/60',
    suffixColor: 'text-violet-700 dark:text-violet-300',
  },
  currency: {
    id: 'currency',
    label: 'Financiero',
    icon: DollarSign,
    accentColor: '#10B981',
    iconBg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    iconColor: 'text-emerald-700 dark:text-emerald-300',
    accentBorder: 'border-emerald-500/30 dark:border-emerald-500/40',
    glowHover: 'hover:border-emerald-500/50 hover:shadow-[0_8px_25px_-4px_rgba(16,185,129,0.22)]',
    tagBg: 'bg-emerald-50 dark:bg-emerald-950/60',
    tagText: 'text-emerald-700 dark:text-emerald-300',
    tagBorder: 'border-emerald-200 dark:border-emerald-800/60',
    suffixColor: 'text-emerald-700 dark:text-emerald-300',
  },
  density: {
    id: 'density',
    label: 'Concentración',
    icon: Activity,
    accentColor: '#F59E0B',
    iconBg: 'bg-amber-500/10 dark:bg-amber-500/20',
    iconColor: 'text-amber-700 dark:text-amber-300',
    accentBorder: 'border-amber-500/30 dark:border-amber-500/40',
    glowHover: 'hover:border-amber-500/50 hover:shadow-[0_8px_25px_-4px_rgba(245,158,11,0.22)]',
    tagBg: 'bg-amber-50 dark:bg-amber-950/60',
    tagText: 'text-amber-700 dark:text-amber-300',
    tagBorder: 'border-amber-200 dark:border-amber-800/60',
    suffixColor: 'text-amber-700 dark:text-amber-300',
  },
  volume: {
    id: 'volume',
    label: 'Volumen',
    icon: Layers,
    accentColor: '#06B6D4',
    iconBg: 'bg-cyan-500/10 dark:bg-cyan-500/20',
    iconColor: 'text-cyan-700 dark:text-cyan-300',
    accentBorder: 'border-cyan-500/30 dark:border-cyan-500/40',
    glowHover: 'hover:border-cyan-500/50 hover:shadow-[0_8px_25px_-4px_rgba(6,182,212,0.22)]',
    tagBg: 'bg-cyan-50 dark:bg-cyan-950/60',
    tagText: 'text-cyan-700 dark:text-cyan-300',
    tagBorder: 'border-cyan-200 dark:border-cyan-800/60',
    suffixColor: 'text-cyan-700 dark:text-cyan-300',
  },
};

/**
 * Detects the visual archetype of a KPI based on its title, value, and subtitle.
 */
function detectArchetype(title: string, value: string | number, subtitle?: string): ArchetypeId {
  const t = (title || '').toLowerCase();
  const s = (subtitle || '').toLowerCase();
  const v = String(value || '').toLowerCase();

  // Percentage
  if (
    v.includes('%') ||
    t.includes('porcentaje') ||
    t.includes('proporción') ||
    t.includes('proporcion') ||
    t.includes('ratio') ||
    t.includes('tasa') ||
    t.includes('pct') ||
    s.includes('proporción') ||
    s.includes('porcentaje')
  ) {
    return 'percentage';
  }

  // Currency
  if (
    v.includes('$') ||
    v.includes('€') ||
    t.includes('monto') ||
    t.includes('precio') ||
    t.includes('costo') ||
    t.includes('ingreso') ||
    t.includes('gasto') ||
    t.includes('venta') ||
    t.includes('facturación') ||
    t.includes('revenue')
  ) {
    return 'currency';
  }

  // Density / Frequency / Average
  if (
    t.includes('densidad') ||
    t.includes('promedio') ||
    t.includes('media') ||
    t.includes('frecuencia') ||
    t.includes('concentración') ||
    t.includes('índice') ||
    t.includes('indice') ||
    s.includes('densidad') ||
    s.includes('frecuencia')
  ) {
    return 'density';
  }

  // Default: Volume / Count / General Metric
  return 'volume';
}

interface ParsedTitle {
  cleanTitle: string;
  filterTag: string | null;
  fullTitle: string;
}

/**
 * Extracts clean, punchy title and active condition/filter pills from verbose LLM titles.
 * E.g. "Número Total de Registros con Campo_3 = 1" -> Title: "Total Registros", Tag: "Campo_3 = 1"
 */
function parseKPITitle(rawTitle: string): ParsedTitle {
  if (!rawTitle) {
    return { cleanTitle: 'Métrica', filterTag: null, fullTitle: '' };
  }
  const fullTitle = rawTitle.trim();

  let cleanTitle = fullTitle;
  let filterTag: string | null = null;

  // Pattern: "... con [condition]", "... donde [condition]", "... para [condition]"
  const conditionMatch = fullTitle.match(/^(.*?)\s+(?:con|donde|filtrado por|para)\s+(.*)$/i);
  if (conditionMatch) {
    cleanTitle = conditionMatch[1].trim();
    filterTag = conditionMatch[2].trim();
  } else if (fullTitle.includes(':')) {
    const parts = fullTitle.split(':');
    cleanTitle = parts[0].trim();
    filterTag = parts.slice(1).join(':').trim();
  }

  // Clean boilerplate prefixes from cleanTitle
  cleanTitle = cleanTitle
    .replace(/^Número Total de\s+/i, 'Total ')
    .replace(/^Número de\s+/i, 'Total ')
    .replace(/^Cantidad Total de\s+/i, 'Total ')
    .replace(/^Cantidad de\s+/i, 'Total ')
    .replace(/^Porcentaje de Registros/i, 'Porcentaje')
    .replace(/^Densidad de Registros/i, 'Densidad Registros')
    .replace(/^Total de Registros/i, 'Total Registros')
    .trim();

  if (!cleanTitle || cleanTitle.toLowerCase() === 'total') {
    cleanTitle = 'Total Registros';
  }

  if (filterTag) {
    filterTag = filterTag.replace(/^[\("']+|[\)"']+$/g, '').trim();
  }

  return { cleanTitle, filterTag, fullTitle };
}

interface FormattedKPIValue {
  prefix: string;
  numberPart: string;
  suffix: string;
  rawPercentNum: number | null;
}

/**
 * Formats value with separated prefix, large number part, and stylish unit suffix.
 * Automatically handles % for rates and clean K/M suffixes.
 */
function formatKPIValue(value: string | number, archetype: ArchetypeId): FormattedKPIValue {
  let strVal = String(value ?? '').trim();

  // If percentage archetype but raw number (e.g. 24 or 0.24)
  let rawPercentNum: number | null = null;
  if (archetype === 'percentage') {
    const num = parseFloat(strVal.replace(/[^0-9.-]+/g, ''));
    if (!isNaN(num)) {
      if (!strVal.includes('%')) {
        if (num > 0 && num <= 1) {
          rawPercentNum = num * 100;
          strVal = `${(num * 100).toFixed(1)}%`;
        } else {
          rawPercentNum = num;
          strVal = `${num % 1 === 0 ? num.toFixed(0) : num.toFixed(1)}%`;
        }
      } else {
        rawPercentNum = num;
      }
    }
  }

  // Currency prefix handling
  let prefix = '';
  if (strVal.startsWith('$') || strVal.startsWith('€')) {
    prefix = strVal[0];
    strVal = strVal.slice(1).trim();
  } else if (archetype === 'currency' && !strVal.startsWith('$')) {
    prefix = '$';
  }

  // Suffix extraction (%, K, M, B)
  let suffix = '';
  const suffixMatch = strVal.match(/([%KMBkmb]+)$/);
  if (suffixMatch) {
    suffix = suffixMatch[1].toUpperCase();
    strVal = strVal.slice(0, -suffixMatch[0].length).trim();
  } else {
    // If it's a raw number without suffix, format with standard K/M if applicable
    const rawNum = typeof value === 'number' ? value : parseFloat(strVal.replace(/[^0-9.-]+/g, ''));
    if (!isNaN(rawNum) && archetype !== 'percentage') {
      const formatted = formatMetricNumber(rawNum, false);
      const match = formatted.match(/([KMBkmb]+)$/);
      if (match) {
        suffix = match[1].toUpperCase();
        strVal = formatted.slice(0, -match[0].length).trim();
      } else {
        strVal = formatted;
      }
    }
  }

  return {
    prefix,
    numberPart: strVal || '0',
    suffix,
    rawPercentNum,
  };
}

/**
 * Eliminates repetitive AI boilerplate phrases from KPI subtitles.
 */
function sanitizeSubtitle(
  rawSubtitle: string | undefined,
  archetype: ArchetypeId,
  filterTag: string | null
): string {
  if (!rawSubtitle) {
    if (filterTag) return `Cumplen condición: ${filterTag}`;
    if (archetype === 'percentage') return 'Proporción respecto al total analizado';
    if (archetype === 'density') return 'Concentración observada en muestra';
    if (archetype === 'volume') return 'Volumen total evaluado en la consulta';
    return 'Métrica analítica consolidada';
  }

  let cleaned = rawSubtitle.trim();

  // Strip boilerplate prefixes
  cleaned = cleaned
    .replace(/^Este KPI indica(?: la| el| los| las| cuántos)?\s*/i, '')
    .replace(/^Este KPI muestra(?: la| el| los| las)?\s*/i, '')
    .replace(/^Este indicador refleja(?: la| el| los| las)?\s*/i, '')
    .replace(/^Este KPI calcula(?: la| el| los| las)?\s*/i, '')
    .replace(/^Indica cuántos registros\s*/i, 'Registros que ')
    .replace(
      /^Indica la cantidad de registros que cumplen con la condición especificada\.?/i,
      'Registros que cumplen con el filtro especificado'
    )
    .replace(
      /^Muestra la proporción de registros en relación con el total\.?/i,
      'Proporción respecto al total de registros'
    )
    .trim();

  if (!cleaned || cleaned.length < 4) {
    if (filterTag) return `Condición activa: ${filterTag}`;
    if (archetype === 'percentage') return 'Proporción respecto al universo total';
    return 'Total consolidado en base de datos';
  }

  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

// -------------------------------------------------------------
// Pure Inline Micro-Visualizations (Zero Chart Lag, 100% SVG)
// -------------------------------------------------------------

const PercentageTrack: React.FC<{ percent: number }> = ({ percent }) => {
  const clamped = Math.max(4, Math.min(100, Math.round(percent)));
  return (
    <div className="w-full mt-3 space-y-1.5" aria-hidden="true">
      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 dark:text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
          Proporción
        </span>
        <span className="font-semibold text-violet-700 dark:text-violet-300">{clamped}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-200/80 dark:bg-slate-800 rounded-full overflow-hidden relative">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-600 via-purple-500 to-indigo-400 transition-all duration-700 ease-out shadow-[0_0_8px_rgba(139,92,246,0.5)]"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
};
// -------------------------------------------------------------
// Single KPI Card Component with High-Interactivity & Polish
// -------------------------------------------------------------

interface SingleCardProps {
  kpi: KPICard;
  idx: number;
}

const SingleKPICard: React.FC<SingleCardProps> = ({ kpi, idx }) => {
  const [copied, setCopied] = useState(false);

  const archetypeId = detectArchetype(kpi.title, kpi.value, kpi.subtitle);
  const theme = ARCHETYPE_THEMES[archetypeId];
  const { cleanTitle, filterTag, fullTitle } = parseKPITitle(kpi.title);
  const { prefix, numberPart, suffix, rawPercentNum } = formatKPIValue(kpi.value, archetypeId);
  const cleanSubtitle = sanitizeSubtitle(kpi.subtitle, archetypeId, filterTag);

  const isPositive = kpi.change_direction === 'positive';
  const isNegative = kpi.change_direction === 'negative';

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    const copyText = `${cleanTitle}: ${prefix}${numberPart}${suffix}${filterTag ? ` (${filterTag})` : ''} - ${cleanSubtitle}`;
    void copyToClipboard(copyText).then((ok: boolean) => {
      if (!ok) return;
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    });
  };

  const IconComponent = theme.icon;

  return (
    <div
      className={`relative group rounded-2xl p-4 bg-white/90 dark:bg-dark-card/90 backdrop-blur-md border border-slate-200/90 dark:border-dark-border/80 shadow-md flex flex-col justify-between transition-all duration-200 ease-out hover:-translate-y-1 ${theme.glowHover}`}
      title={fullTitle}
    >
      {/* Top Header: Icon + Title + Status Pill */}
      <div>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className={`p-2 rounded-xl border ${theme.iconBg} ${theme.accentBorder} shrink-0 transition-transform group-hover:scale-105`}
            >
              <IconComponent className={`w-4 h-4 ${theme.iconColor}`} />
            </div>
            <div className="min-w-0">
              <span className="text-[12px] font-bold text-slate-800 dark:text-slate-100 truncate block tracking-tight">
                {cleanTitle}
              </span>
              {filterTag ? (
                <span
                  className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800/90 px-1.5 py-0.5 rounded-md border border-slate-200 dark:border-slate-700/70 truncate max-w-[130px] mt-0.5"
                  title={`Criterio de filtro: ${filterTag}`}
                >
                  <Filter className="w-2.5 h-2.5 opacity-60 shrink-0" />
                  <span className="truncate">{filterTag}</span>
                </span>
              ) : (
                <span className="text-[10px] font-medium text-slate-500 dark:text-gray-400 block truncate mt-0.5">
                  {theme.label}
                </span>
              )}
            </div>
          </div>

          {/* Contextual Direction / Category Badge (No more redundant identical • ESTABLE) */}
          <div className="flex items-center gap-1 shrink-0">
            {kpi.change_direction && (isPositive || isNegative) ? (
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                  isPositive
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                    : 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30'
                }`}
              >
                {isPositive ? (
                  <TrendingUp className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                )}
                {isPositive ? 'En Alza' : 'Descenso'}
              </span>
            ) : (
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${theme.tagBg} ${theme.tagText} ${theme.tagBorder}`}
              >
                {archetypeId === 'percentage'
                  ? 'Ratio'
                  : archetypeId === 'currency'
                  ? 'Moneda'
                  : archetypeId === 'density'
                  ? 'Densidad'
                  : 'Muestra'}
              </span>
            )}

            {/* Quick 1-click Copy Action */}
            <button
              type="button"
              onClick={handleCopy}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
              title="Copiar valor de KPI al portapapeles"
              aria-label="Copiar valor de KPI"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Metric Display: High Impact Numbers with Suffix Unit Styling */}
        <div className="mt-3">
          <div className="flex items-baseline gap-1 font-mono">
            {prefix && (
              <span className="text-base font-bold text-slate-500 dark:text-slate-400">
                {prefix}
              </span>
            )}
            <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white tabular-nums group-hover:scale-[1.01] transition-transform origin-left">
              {numberPart}
            </span>
            {suffix && (
              <span className={`text-base font-bold tracking-tight ${theme.suffixColor}`}>
                {suffix}
              </span>
            )}
          </div>

          {/* Anti-Slop Subtitle */}
          <p className="text-[11px] text-slate-600 dark:text-gray-400 mt-1 line-clamp-1 leading-snug">
            {cleanSubtitle}
          </p>
        </div>
      </div>

      {/* Embedded Micro-Visualizations */}
      <div>
        {archetypeId === 'percentage' && (
          <PercentageTrack percent={rawPercentNum ?? (parseFloat(numberPart) || 24)} />
        )}
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Main KPISection Export
// -------------------------------------------------------------

export const KPISection: React.FC<KPISectionProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) {
    return null;
  }

  // Choose responsive column layout based on card count
  const gridLayout =
    kpis.length === 1
      ? 'grid-cols-1 max-w-sm'
      : kpis.length === 2
      ? 'grid-cols-1 sm:grid-cols-2 max-w-2xl'
      : kpis.length === 3
      ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
      : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4';

  return (
    <div className="w-full space-y-2">
      <div className={`grid ${gridLayout} gap-3.5`}>
        {kpis.map((kpi, idx) => (
          <SingleKPICard key={kpi.title ? `${kpi.title}-${idx}` : idx} kpi={kpi} idx={idx} />
        ))}
      </div>
    </div>
  );
};
