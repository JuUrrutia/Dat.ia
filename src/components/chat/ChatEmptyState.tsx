import React, { useEffect, useState } from 'react';
import logoDatiaDark from '../../pages/Logo_datia_2.png';
import logoDatiaLight from '../../pages/Logo_Datia_3.png';

interface ChatEmptyStateProps {
  promptSuggestions: string[];
  onSelectSuggestion: (suggestion: string) => void;
}

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({
  promptSuggestions,
  onSelectSuggestion,
}) => {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof document === 'undefined') return 'dark';
    return document.documentElement.classList.contains('light') ? 'light' : 'dark';
  });

  useEffect(() => {
    const syncTheme = () => {
      const isLight = document.documentElement.classList.contains('light');
      setTheme(isLight ? 'light' : 'dark');
    };

    syncTheme();
    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    return () => observer.disconnect();
  }, []);

  const currentLogo = theme === 'dark' ? logoDatiaDark : logoDatiaLight;

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-5 sm:space-y-6 p-4">
      <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-white/70 dark:bg-transparent flex items-center justify-center shadow-xl shadow-brand-500/20 animate-bounce-subtle overflow-hidden border border-white/30 dark:border-transparent">
        <img src={currentLogo} alt="Logo de Dat.ia" className="w-full h-full object-contain p-1" />
      </div>

      <div className="space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
          ¿Qué deseas analizar de la empresa hoy?
        </h2>
        <p className="text-xs text-gray-400 leading-relaxed max-w-md mx-auto">
          Pregunta en lenguaje natural sobre finanzas, operaciones, incidentes o recursos. La IA local validará los permisos RBAC antes de consultar la BD corporativa.
        </p>
      </div>

      {/* Dynamic Suggestions Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 w-full max-w-xl text-left">
        {promptSuggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSelectSuggestion(suggestion)}
            className="p-3 sm:p-3.5 rounded-xl bg-dark-surface hover:bg-dark-card border border-dark-border hover:border-brand-500/40 text-xs text-gray-300 hover:text-white transition-colors text-left group flex items-start space-x-2.5 shadow-sm"
          >
            <span className="text-brand-400 font-bold">›</span>
            <span className="group-hover:translate-x-0.5 transition-transform leading-snug">{suggestion}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
