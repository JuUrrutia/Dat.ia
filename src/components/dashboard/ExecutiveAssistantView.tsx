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
    <div className="w-full space-y-3 animate-fadeIn font-sans">
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
      <div className="glass-panel border border-white/10 rounded-2xl p-5 sm:p-6 shadow-2xl space-y-4">
        <AssistantMarkdownBody rawContent={rawContent} />

        {/* Footer Technical Metadata & Traceability */}
        <div className="pt-3.5 border-t border-dark-border/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs text-gray-400">
          <div className="flex items-center space-x-3 flex-wrap gap-y-1">
            <span className="inline-flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-md border border-emerald-500/20 text-[10px] font-semibold">
              <CheckCircle2 className="w-3 h-3" />
              <span>Gobernanza AST Aprobada</span>
            </span>
            <span className="text-[11px]">
              Latencia: <strong className="text-gray-200 font-mono">{result.traceability?.execution_time_ms || 0} ms</strong>
            </span>
          </div>

          {onOpenTraceability && (
            <button
              type="button"
              onClick={onOpenTraceability}
              className="flex items-center space-x-1 text-xs text-brand-300 hover:text-brand-200 transition-colors font-medium self-start sm:self-auto"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
              <span>Ver Auditoría SQL</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
