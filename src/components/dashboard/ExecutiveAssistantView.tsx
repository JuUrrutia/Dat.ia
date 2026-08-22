import React, { useState } from 'react';
import { QueryResult } from '../../types';
import { DataGridTable } from '../datagrid/DataGridTable';
import {
  Sparkles,
  Copy,
  Check,
  ShieldCheck,
  Database,
  Lightbulb,
  CheckCircle2,
  Table as TableIcon,
  BarChart3,
  ChevronDown,
  ChevronUp,
  FileText,
  Zap,
} from 'lucide-react';

interface ExecutiveAssistantViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
}

// Helper to parse sections/ideas from markdown
const parseMarkdownContent = (text: string) => {
  const lines = text.split('\n');
  const sections: Array<{
    id: string;
    type: 'h2' | 'h3' | 'callout' | 'bullet' | 'paragraph';
    content: string;
    number?: number;
  }> = [];

  let currentParagraph = '';

  const addSection = (
    type: 'h2' | 'h3' | 'callout' | 'bullet' | 'paragraph',
    content: string,
    number?: number
  ) => {
    const id = `sec-${sections.length}-${type}`;
    sections.push({
      id,
      type,
      content,
      ...(number !== undefined ? { number } : {}),
    });
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

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

const formatInlineMarkdown = (text: string, keyPrefix: string = 'inline') => {
  // Replace **bold** with <strong> and `code` with <code>
  const rawParts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  let counter = 0;
  const parts = rawParts.map((content) => {
    counter += 1;
    return {
      id: `${keyPrefix}-part-${counter}`,
      content,
    };
  });

  return parts.map((part) => {
    if (part.content.startsWith('**') && part.content.endsWith('**')) {
      return (
        <strong key={part.id} className="text-amber-300 font-semibold">
          {part.content.slice(2, -2)}
        </strong>
      );
    }
    if (part.content.startsWith('`') && part.content.endsWith('`')) {
      return (
        <code key={part.id} className="bg-zinc-950 px-1.5 py-0.5 rounded text-amber-300 font-mono text-xs border border-white/10">
          {part.content.slice(1, -1)}
        </code>
      );
    }
    return part.content;
  });
};

interface ExecutiveAssistantHeaderProps {
  result: QueryResult;
  flags: {
    canSwitchToStudio: boolean;
    showSupportData: boolean;
    copied: boolean;
  };
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
  onToggleSupportData: () => void;
  onCopy: () => void;
}

const ExecutiveAssistantHeader: React.FC<ExecutiveAssistantHeaderProps> = ({
  result,
  flags,
  onSwitchToStudio,
  onSwitchToReport,
  onToggleSupportData,
  onCopy,
}) => {
  const hasSupportData = Boolean(result.data_rows && result.data_rows.length > 0);

  return (
    <div className="bg-gradient-to-r from-zinc-900/95 via-zinc-900/70 to-zinc-950/95 border border-white/10 rounded-3xl p-6 shadow-2xl backdrop-blur-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start sm:items-center space-x-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-amber-500/20 to-amber-500/5 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10 shrink-0">
            <Lightbulb className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
              <h2 className="text-base font-bold text-white tracking-tight">
                {result.response_type === 'greeting'
                  ? 'Asistente DATIA'
                  : result.response_type === 'explanation'
                  ? 'Explicación Conceptual'
                  : result.response_type === 'data_analysis'
                  ? 'Respuesta Analítica IA'
                  : 'Asesoría Estratégica IA'}
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" />
                {result.response_type === 'explanation'
                  ? 'Explicación'
                  : result.response_type === 'greeting'
                  ? 'Conversación'
                  : result.response_type === 'data_analysis'
                  ? 'Interpretación de Datos'
                  : 'Estrategia'}
              </span>
              {result.grounding_info && (
                <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <Database className="w-2.5 h-2.5" />
                  <span>Datos Reales BD</span>
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-1">
              Respuesta generada para "{result.question}" a partir de la base de datos activa.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-start md:self-auto flex-wrap gap-y-2">
          {flags.canSwitchToStudio && onSwitchToStudio && (
            <button
              onClick={onSwitchToStudio}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 hover:text-white transition-colors"
              title="Ver proyección en Studio Analítico"
            >
              <BarChart3 className="w-3.5 h-3.5 text-amber-400" />
              <span>Ver en Studio</span>
            </button>
          )}

          {result.executive_report && onSwitchToReport && (
            <button
              onClick={onSwitchToReport}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/10 hover:text-white transition-colors"
              title="Ver formato informe"
            >
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span>Informe</span>
            </button>
          )}

          {hasSupportData && (
            <button
              onClick={onToggleSupportData}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                flags.showSupportData
                  ? 'bg-amber-500 text-zinc-950 border-amber-400 font-bold'
                  : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-white/10 hover:text-white'
              }`}
              title="Ver registros consultados en SQLite"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Datos de Apoyo ({result.data_rows?.length || 0})</span>
              {flags.showSupportData ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
            </button>
          )}

          <button
            onClick={onCopy}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-colors shadow-sm"
            title="Copiar respuesta al portapapeles"
          >
            {flags.copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{flags.copied ? '¡Copiado!' : 'Copiar'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export const ExecutiveAssistantView: React.FC<ExecutiveAssistantViewProps> = ({
  result,
  onOpenTraceability,
  onSwitchToStudio,
  onSwitchToReport,
}) => {
  const [copied, setCopied] = useState(false);
  const [showSupportData, setShowSupportData] = useState(false);

  const rawContent = result.conversational_response || result.summary_text || '';

  const handleCopy = () => {
    navigator.clipboard.writeText(rawContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const parsedSections = parseMarkdownContent(rawContent);

  const hasSupportData = Boolean(result.data_rows && result.data_rows.length > 0);
  const canSwitchToStudio = Boolean(
    result.chart_type &&
    result.chart_type !== 'none' &&
    result.chart_option &&
    result.chart_option.series &&
    result.chart_option.series.length > 0
  );

  return (
    <div className="w-full space-y-5 animate-fadeIn">
      <ExecutiveAssistantHeader
        result={result}
        flags={{
          canSwitchToStudio,
          showSupportData,
          copied,
        }}
        onSwitchToStudio={onSwitchToStudio}
        onSwitchToReport={onSwitchToReport}
        onToggleSupportData={() => setShowSupportData(!showSupportData)}
        onCopy={handleCopy}
      />

      {/* Support Data Collapsible Section */}
      {showSupportData && hasSupportData && (
        <div className="bg-gradient-to-br from-zinc-900/90 via-zinc-900/60 to-zinc-950/90 border border-white/10 rounded-3xl p-6 shadow-2xl space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white tracking-tight">
                Registros de Respaldo Extraídos de SQLite ({result.data_rows?.length || 0})
              </h3>
            </div>
            <span className="text-xs text-zinc-400 bg-zinc-950 px-3 py-1 rounded-lg border border-white/5">
              {result.traceability?.schema_tables_used?.join(', ') || 'SQLite'}
            </span>
          </div>
          <DataGridTable
            columns={result.data_columns}
            rows={result.data_rows}
            question={result.question}
            auditLogId={result.traceability?.audit_log_id || result.audit_log_id}
          />
        </div>
      )}

      {/* Main Content Area */}
      <div className="bg-gradient-to-br from-zinc-900/95 via-zinc-900/60 to-zinc-950/95 border border-white/10 rounded-3xl p-7 shadow-2xl space-y-6">
        {parsedSections.length > 0 ? (
          <div className="space-y-4">
            {parsedSections.map((sec) => {
              if (sec.type === 'h2') {
                return (
                  <div key={sec.id} className="pb-3 border-b border-white/10 flex items-center space-x-2.5">
                    <div className="w-2 h-2 rounded-full bg-amber-400" />
                    <h3 className="text-base font-bold text-white tracking-tight">
                      {sec.content}
                    </h3>
                  </div>
                );
              }

              if (sec.type === 'h3') {
                return (
                  <div
                    key={sec.id}
                    className="flex items-center space-x-3 pt-2 mt-4 first:mt-0"
                  >
                    {sec.number !== undefined ? (
                      <div className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-300 font-extrabold flex items-center justify-center text-xs shrink-0 border border-amber-500/30 shadow-md shadow-amber-500/10">
                        {sec.number}
                      </div>
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-amber-400" />
                    )}
                    <h4 className="text-sm font-bold text-amber-300/95 tracking-tight">
                      {sec.content}
                    </h4>
                  </div>
                );
              }

              if (sec.type === 'callout') {
                return (
                  <blockquote
                    key={sec.id}
                    className="border-l-2 border-amber-400/80 bg-amber-500/5 px-4 py-2.5 rounded-r-xl text-xs text-amber-200/90 leading-relaxed italic my-2"
                  >
                    {formatInlineMarkdown(sec.content, sec.id)}
                  </blockquote>
                );
              }

              if (sec.type === 'bullet') {
                return (
                  <div
                    key={sec.id}
                    className="flex items-start space-x-2.5 text-sm text-zinc-300 leading-relaxed pl-1 py-0.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 shrink-0" />
                    <div className="leading-relaxed font-normal flex-1">
                      {formatInlineMarkdown(sec.content, sec.id)}
                    </div>
                  </div>
                );
              }

              return (
                <p
                  key={sec.id}
                  className="text-sm text-zinc-200 leading-relaxed font-normal my-1"
                >
                  {formatInlineMarkdown(sec.content, sec.id)}
                </p>
              );
            })}
          </div>
        ) : (
          <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {rawContent}
          </div>
        )}

        {/* Footer Technical Metadata & Traceability */}
        <div className="pt-5 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-zinc-400">
          <div className="flex items-center space-x-3 flex-wrap gap-y-1">
            <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-md border border-emerald-500/20 font-medium">
              <CheckCircle2 className="w-3 h-3" />
              <span>Gobernanza AST Aprobada</span>
            </span>
            <span>
              Latencia: <strong className="text-zinc-200">{result.traceability?.execution_time_ms || 0} ms</strong>
            </span>
            {result.grounding_info && (
              <span className="hidden sm:inline text-zinc-500">|</span>
            )}
            {result.grounding_info && (
              <span className="text-zinc-300 truncate max-w-md">
                {result.grounding_info}
              </span>
            )}
          </div>

          {onOpenTraceability && (
            <button
              onClick={onOpenTraceability}
              className="flex items-center space-x-1.5 text-xs text-amber-400 hover:text-amber-300 transition-colors self-start sm:self-auto font-medium"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Ver Auditoría SQL</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
