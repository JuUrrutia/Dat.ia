import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { copyToClipboard } from '../../../../shared/clipboard';

export interface TableData {
  headers: string[];
  alignments: ('left' | 'center' | 'right')[];
  rows: string[][];
}

export interface MarkdownSection {
  id: string;
  type: 'h2' | 'h3' | 'callout' | 'bullet' | 'paragraph' | 'table';
  content: string;
  number?: number;
  tableData?: TableData;
}

const isTableLine = (line: string): boolean => {
  const trimmed = line.trim();
  return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length >= 3;
};

const isSeparatorLine = (line: string): boolean => {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return false;
  const inner = trimmed.slice(1, -1);
  return /^[\s\-:|]+$/.test(inner) && inner.includes('-');
};

const parseTableRow = (line: string): string[] => {
  return line
    .trim()
    .slice(1, -1)
    .split('|')
    .map((c) => c.trim());
};

const parseAlignments = (line: string): ('left' | 'center' | 'right')[] => {
  const cols = parseTableRow(line);
  return cols.map((col) => {
    const trimmed = col.trim();
    if (trimmed.startsWith(':') && trimmed.endsWith(':')) return 'center';
    if (trimmed.endsWith(':')) return 'right';
    return 'left';
  });
};

export const parseMarkdownContent = (text: string) => {
  const lines = text.split('\n');
  const sections: MarkdownSection[] = [];

  let currentParagraph = '';

  const addSection = (
    type: MarkdownSection['type'],
    content: string,
    number?: number,
    tableData?: TableData
  ) => {
    const id = `sec-${sections.length}-${type}`;
    sections.push({
      id,
      type,
      content,
      ...(number !== undefined ? { number } : {}),
      ...(tableData ? { tableData } : {}),
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    // Check for Markdown table: current line is table row and next line is separator
    if (isTableLine(line) && i + 1 < lines.length && isSeparatorLine(lines[i + 1])) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }

      const headers = parseTableRow(line);
      const alignments = parseAlignments(lines[i + 1]);
      const rows: string[][] = [];

      i += 2; // Move past header and separator
      while (i < lines.length && isTableLine(lines[i])) {
        rows.push(parseTableRow(lines[i]));
        i++;
      }
      i--; // Adjust for loop increment

      addSection('table', '', undefined, { headers, alignments, rows });
      continue;
    }

    if (line.startsWith('## ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('h2', line.replace(/^##\s+/, ''));
    } else if (line.startsWith('### ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      const h3Text = line.replace(/^###\s+/, '');
      const numMatch = h3Text.match(/^(\d+)[.\s-]+(.*)/);
      if (numMatch) {
        addSection('h3', numMatch[2].trim(), parseInt(numMatch[1], 10));
      } else {
        addSection('h3', h3Text);
      }
    } else if (line.startsWith('> ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('callout', line.replace(/^>\s+/, ''));
    } else if (line.startsWith('* ') || line.startsWith('- ')) {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
      addSection('bullet', line.replace(/^[\*\-]\s+/, ''));
    } else if (line === '') {
      if (currentParagraph) {
        addSection('paragraph', currentParagraph);
        currentParagraph = '';
      }
    } else {
      currentParagraph = currentParagraph ? `${currentParagraph} ${line}` : line;
    }
  }

  if (currentParagraph) {
    addSection('paragraph', currentParagraph);
  }

  return sections;
};

const GLOSSARY_DICT: Record<string, string> = {
  kpi: 'Key Performance Indicator: Métrica cuantitativa clave para evaluar el éxito de un objetivo empresarial.',
  roi: 'Return on Investment: Ratio financiero que evalúa el beneficio obtenido respecto a la inversión realizada.',
  ebitda: 'Beneficio operativo bruto antes de deducir intereses, impuestos, depreciaciones y amortizaciones.',
  cac: 'Costo de Adquisición de Clientes: Inversión requerida para conseguir un nuevo cliente.',
  ltv: 'Lifetime Value: Valor monetario estimado que genera un cliente durante toda su relación comercial.',
  churn: 'Tasa de Cancelación: Porcentaje de clientes o suscripciones que abandonan el servicio en un periodo.',
  rbac: 'Role-Based Access Control: Gobernanza de seguridad que restringe el acceso a datos según el rol asignado.',
  ast: 'Abstract Syntax Tree: Árbol de sintaxis analizado para blindar y verificar la seguridad de la consulta SQL.',
  arpu: 'Average Revenue Per User: Ingreso promedio generado por cada usuario activo.',
};

export const formatInlineMarkdown = (text: string, keyPrefix: string = 'inline') => {
  const rawParts = text.split(/(\*\*.*?\*\*|`.*?`|\[OPORTUNIDAD\]|\[RIESGO\]|\[ESTABLE\])/gi);
  let counter = 0;
  const parts = rawParts.map((content) => {
    counter += 1;
    return {
      id: `${keyPrefix}-part-${counter}`,
      content,
    };
  });

  return parts.map((part) => {
    const upper = part.content.toUpperCase();
    if (upper === '[OPORTUNIDAD]') {
      return (
        <span
          key={part.id}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border border-emerald-500/40 mr-1.5 align-baseline shadow-2xs"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          OPORTUNIDAD
        </span>
      );
    }
    if (upper === '[RIESGO]') {
      return (
        <span
          key={part.id}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-rose-500/20 text-rose-800 dark:text-rose-300 border border-rose-500/40 mr-1.5 align-baseline shadow-2xs"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
          RIESGO
        </span>
      );
    }
    if (upper === '[ESTABLE]') {
      return (
        <span
          key={part.id}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-blue-500/20 text-blue-800 dark:text-blue-300 border border-blue-500/40 mr-1.5 align-baseline shadow-2xs"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          ESTABLE
        </span>
      );
    }

    if (part.content.startsWith('**') && part.content.endsWith('**')) {
      return (
        <strong key={part.id} className="text-gray-900 dark:text-white font-semibold">
          {part.content.slice(2, -2)}
        </strong>
      );
    }
    if (part.content.startsWith('`') && part.content.endsWith('`')) {
      return (
        <code key={part.id} className="bg-slate-100 dark:bg-dark-base px-1.5 py-0.5 rounded text-cyan-800 dark:text-cyan-300 font-mono text-xs border border-slate-200 dark:border-dark-border">
          {part.content.slice(1, -1)}
        </code>
      );
    }

    // Process glossary terms in regular text
    const words = part.content.split(/(\b(?:KPI|ROI|EBITDA|CAC|LTV|Churn|RBAC|AST|ARPU)\b)/gi);
    if (words.length > 1) {
      return (
        <React.Fragment key={part.id}>
          {words.map((w, idx) => {
            const def = GLOSSARY_DICT[w.toLowerCase()];
            if (def) {
              return (
                <abbr
                  key={`${part.id}-term-${idx}`}
                  title={def}
                  tabIndex={0}
                  className="cursor-help font-semibold text-brand-700 dark:text-brand-300 underline decoration-dotted decoration-brand-500/70 hover:text-brand-900 dark:hover:text-brand-100 transition-colors"
                >
                  {w}
                </abbr>
              );
            }
            return w;
          })}
        </React.Fragment>
      );
    }

    return part.content;
  });
};

interface MarkdownTableComponentProps {
  tableData: TableData;
  id: string;
}

const MarkdownTableComponent: React.FC<MarkdownTableComponentProps> = ({ tableData, id }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const headerLine = tableData.headers.join('\t');
    const rowLines = tableData.rows.map((r) => r.join('\t')).join('\n');
    void copyToClipboard(`${headerLine}\n${rowLines}`).then((ok: boolean) => {
      if (!ok) return;
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const isNullLike = (val: string) => {
    const lower = val.trim().toLowerCase();
    return lower === '' || lower === 'null' || lower === 'none' || lower === '-' || lower === 'n/a';
  };

  return (
    <div className="my-3 rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-xs overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-50/70 dark:bg-zinc-800/40 border-b border-slate-200/80 dark:border-zinc-800/80">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-zinc-400">
          Tabla ({tableData.rows.length} {tableData.rows.length === 1 ? 'fila' : 'filas'})
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors px-1.5 py-0.5 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 cursor-pointer"
          title="Copiar tabla para Excel / Google Sheets"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-500" />
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">Copiado</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copiar</span>
            </>
          )}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 dark:bg-zinc-800/80 border-b border-slate-200 dark:border-zinc-800 text-[11px] text-slate-600 dark:text-zinc-300 font-semibold uppercase tracking-wider">
              {tableData.headers.map((h, idx) => {
                const align = tableData.alignments[idx] || 'left';
                return (
                  <th
                    key={`${id}-th-${idx}`}
                    className={`px-3.5 py-2.5 whitespace-nowrap ${
                      align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left'
                    }`}
                  >
                    {formatInlineMarkdown(h, `${id}-th-${idx}`)}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/60 text-slate-800 dark:text-zinc-200">
            {tableData.rows.map((row, rIdx) => (
              <tr key={`${id}-tr-${rIdx}`} className="hover:bg-slate-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                {tableData.headers.map((_, cIdx) => {
                  const val = row[cIdx] !== undefined ? row[cIdx] : '';
                  const align = tableData.alignments[cIdx] || 'left';
                  const isNum = !isNaN(Number(val)) && val.trim() !== '';

                  return (
                    <td
                      key={`${id}-td-${rIdx}-${cIdx}`}
                      className={`px-3.5 py-2 whitespace-nowrap ${
                        align === 'center' ? 'text-center' : align === 'right' || isNum ? 'text-right font-mono tabular-nums' : 'text-left'
                      }`}
                    >
                      {isNullLike(val) ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-zinc-500 border border-slate-200 dark:border-zinc-700/60 select-none">
                          NULL
                        </span>
                      ) : (
                        formatInlineMarkdown(val, `${id}-cell-${rIdx}-${cIdx}`)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface AssistantMarkdownBodyProps {
  rawContent: string;
}

export const AssistantMarkdownBody: React.FC<AssistantMarkdownBodyProps> = ({ rawContent }) => {
  const parsedSections = parseMarkdownContent(rawContent);

  if (parsedSections.length === 0) {
    return (
      <div className="text-xs sm:text-sm text-slate-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">
        {rawContent}
      </div>
    );
  }

  return (
    <div className="space-y-3 sm:space-y-4 font-sans text-xs sm:text-sm text-slate-800 dark:text-gray-200">
      {parsedSections.map((sec) => {
        if (sec.type === 'table' && sec.tableData) {
          return <MarkdownTableComponent key={sec.id} tableData={sec.tableData} id={sec.id} />;
        }

        if (sec.type === 'h2') {
          return (
            <div key={sec.id} className="pb-2 border-b border-dark-border/80 flex items-center space-x-2 pt-2">
              <span className="w-2 h-2 rounded-full bg-cyan-500 dark:bg-cyan-400" />
              <h3 className="text-sm sm:text-base font-extrabold text-gray-900 dark:text-white tracking-tight">
                {sec.content}
              </h3>
            </div>
          );
        }

        if (sec.type === 'h3') {
          return (
            <div
              key={sec.id}
              className="flex items-center space-x-2.5 pt-2 mt-3 first:mt-0"
            >
              {sec.number !== undefined ? (
                <div className="w-5 h-5 rounded-md bg-brand-500/15 text-brand-700 dark:text-brand-300 font-bold flex items-center justify-center text-xs shrink-0 border border-brand-500/30">
                  {sec.number}
                </div>
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 dark:bg-indigo-400" />
              )}
              <h4 className="text-xs sm:text-sm font-bold text-gray-900 dark:text-gray-100 tracking-tight">
                {sec.content}
              </h4>
            </div>
          );
        }

        if (sec.type === 'callout') {
          return (
            <blockquote
              key={sec.id}
              className="border-l-2 border-cyan-500 dark:border-cyan-400 bg-cyan-500/10 dark:bg-cyan-500/5 px-3.5 py-2 rounded-r-xl text-xs text-slate-700 dark:text-gray-300 leading-relaxed italic my-2"
            >
              {formatInlineMarkdown(sec.content, sec.id)}
            </blockquote>
          );
        }

        if (sec.type === 'bullet') {
          return (
            <div
              key={sec.id}
              className="flex items-start space-x-2 text-xs sm:text-sm text-slate-700 dark:text-gray-300 leading-relaxed pl-1 py-0.5"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 dark:bg-cyan-400 mt-2 shrink-0" />
              <div className="leading-relaxed font-normal flex-1">
                {formatInlineMarkdown(sec.content, sec.id)}
              </div>
            </div>
          );
        }

        return (
          <p
            key={sec.id}
            className="text-xs sm:text-sm text-slate-800 dark:text-gray-200 leading-relaxed font-normal my-1"
          >
            {formatInlineMarkdown(sec.content, sec.id)}
          </p>
        );
      })}
    </div>
  );
};
