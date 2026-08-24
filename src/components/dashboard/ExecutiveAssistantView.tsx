import React, { useState } from 'react';
import { QueryResult } from '../../types';
import { AssistantHeader } from '../../features/dashboard/components/assistant/AssistantHeader';
import { AssistantSupportData } from '../../features/dashboard/components/assistant/AssistantSupportData';
import { AssistantMarkdownBody } from '../../features/dashboard/components/assistant/AssistantMarkdownBody';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

interface ExecutiveAssistantViewProps {
  result: QueryResult;
  onOpenTraceability?: () => void;
  onSwitchToStudio?: () => void;
  onSwitchToReport?: () => void;
}

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

  const canSwitchToStudio = Boolean(
    result.chart_type &&
    result.chart_type !== 'none' &&
    result.chart_option &&
    result.chart_option.series &&
    result.chart_option.series.length > 0
  );

  return (
    <div className="w-full space-y-5 animate-fadeIn">
      <AssistantHeader
        result={result}
        canSwitchToStudio={canSwitchToStudio}
        showSupportData={showSupportData}
        copied={copied}
        onSwitchToStudio={onSwitchToStudio}
        onSwitchToReport={onSwitchToReport}
        onToggleSupportData={() => setShowSupportData(!showSupportData)}
        onCopy={handleCopy}
      />

      {/* Support Data Collapsible Section */}
      {showSupportData && <AssistantSupportData result={result} />}

      {/* Main Content Area */}
      <div className="bg-gradient-to-br from-zinc-900/95 via-zinc-900/60 to-zinc-950/95 border border-white/10 rounded-3xl p-7 shadow-2xl space-y-6">
        <AssistantMarkdownBody rawContent={rawContent} />

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
