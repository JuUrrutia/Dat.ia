import React from 'react';
import { User, QueryResult } from '../../types';
import { ExecutiveDashboardView } from '../dashboard/ExecutiveDashboardView';
import { Bot, User as UserIcon, ShieldCheck, Server, Wifi, WifiOff } from 'lucide-react';

interface ChatMessageItemProps {
  result: QueryResult;
  user: User | null;
  userRole: string;
  onOpenTraceability: (traceability: QueryResult['traceability']) => void;
}

const PipelineBadge: React.FC<{ source?: string }> = ({ source }) => {
  if (source === 'backend') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
        <Server className="w-3 h-3" />
        Backend + IA Local
      </span>
    );
  }
  if (source === 'llm_direct') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-md">
        <Wifi className="w-3 h-3" />
        LLM Directo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md">
      <WifiOff className="w-3 h-3" />
      Modo Offline
    </span>
  );
};

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  result,
  user,
  userRole,
  onOpenTraceability,
}) => {
  return (
    <div className="space-y-4 sm:space-y-6 pt-4 border-t border-dark-border/40 first:border-0 first:pt-0">
      {/* User Question Bubble */}
      <div className="flex items-start space-x-2 sm:space-x-3 justify-end">
        <div className="bg-brand-600/20 border border-brand-500/30 rounded-2xl rounded-tr-sm p-3.5 sm:p-4 max-w-[85%] sm:max-w-2xl">
          <div className="flex items-center space-x-1.5 text-[10px] text-brand-400 font-semibold mb-1">
            <UserIcon className="w-3 h-3" />
            <span>
              {user?.username} ({userRole})
            </span>
          </div>
          <p className="text-xs sm:text-sm text-white font-medium break-words">{result.question}</p>
        </div>
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-brand-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-600/30">
          <UserIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
      </div>

      {/* System & Analytics Response Bubble */}
      <div className="flex items-start space-x-2 sm:space-x-3">
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shrink-0 shadow-lg shadow-brand-500/20">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>

        <div className="flex-1 space-y-3 sm:space-y-4 max-w-4xl min-w-0">
          {/* Badge / Status Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <PipelineBadge source={result.pipeline_source} />
            <span className="text-[10px] sm:text-[11px] text-gray-400 font-mono">{result.timestamp}</span>
            {result.traceability?.validation_status && (
              <span
                className={`inline-flex items-center gap-1 text-[9px] sm:text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                  result.traceability.validation_status.includes('APROBADO')
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                }`}
              >
                <ShieldCheck className="w-3 h-3" />
                AST: {result.traceability.validation_status}
              </span>
            )}
          </div>

          {/* Render Dynamic Dashboard Views (Report, KPIs, Charts, Tables) */}
          <ExecutiveDashboardView
            result={result}
            onOpenTraceability={() => onOpenTraceability(result.traceability)}
          />
        </div>
      </div>
    </div>
  );
};
