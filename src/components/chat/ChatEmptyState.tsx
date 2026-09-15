import React from 'react';
import { Sparkles, TrendingUp, DollarSign, AlertTriangle, Users, ChevronRight } from 'lucide-react';

interface ChatEmptyStateProps {
  promptSuggestions: string[];
  onSelectSuggestion: (suggestion: string) => void;
}

const SUGGESTION_ICONS = [
  <TrendingUp className="w-4 h-4 text-cyan-400 shrink-0" key="trend" />,
  <DollarSign className="w-4 h-4 text-emerald-400 shrink-0" key="dollar" />,
  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" key="alert" />,
  <Users className="w-4 h-4 text-purple-400 shrink-0" key="users" />,
];

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({
  promptSuggestions,
  onSelectSuggestion,
}) => {
  return (
    <div className="h-full flex flex-col items-center justify-center max-w-3xl mx-auto text-center space-y-6 sm:space-y-8 p-4 font-sans relative">
      {/* Kokonut UI Animated Glowing Ring / Orb Background */}
      <div className="relative flex items-center justify-center">
        <div className="absolute w-32 h-32 rounded-full bg-gradient-to-tr from-brand-500/20 via-indigo-500/20 to-cyan-500/20 blur-2xl pointer-events-none animate-pulse" />
        
        <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-2xl shadow-brand-500/30 border border-white/20 animate-fadeIn">
          <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
        </div>
      </div>

      {/* Hero Content */}
      <div className="space-y-2.5 max-w-lg">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span>DATIA Text-to-SQL Assistant</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
          ¿Qué datos deseas analizar hoy?
        </h2>
        <p className="text-xs sm:text-sm text-gray-400 leading-relaxed max-w-md mx-auto">
          Formula tu pregunta en lenguaje natural. La IA traducirá tu consulta a SQL seguro validado por AST Guardrail según tu perfil RBAC.
        </p>
      </div>

      {/* Dynamic Kokonut UI Categorized Suggestion Cards */}
      {promptSuggestions.length > 0 && (
        <div className="w-full max-w-2xl space-y-3 pt-2">
          <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider text-left pl-1">
            Sugerencias de Consulta Rápidas:
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
            {promptSuggestions.map((suggestion, idx) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSelectSuggestion(suggestion)}
                className="glass-card-interactive p-3.5 rounded-2xl border border-white/10 flex items-center justify-between group text-xs text-gray-300 hover:text-white transition-all shadow-md"
              >
                <div className="flex items-center space-x-3 truncate">
                  <div className="p-2 rounded-xl bg-dark-base border border-dark-border group-hover:border-brand-500/40 transition-colors">
                    {SUGGESTION_ICONS[idx % SUGGESTION_ICONS.length]}
                  </div>
                  <span className="truncate font-medium group-hover:translate-x-0.5 transition-transform">
                    {suggestion}
                  </span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-brand-400 group-hover:translate-x-1 transition-all shrink-0 ml-2" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
