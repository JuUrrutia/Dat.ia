import React from 'react';
import { Send } from 'lucide-react';

interface ChatPromptInputProps {
  promptInput: string;
  setPromptInput: (val: string) => void;
  isGenerating: boolean;
  userRole: string;
  onSubmit: () => void;
}

export const ChatPromptInput: React.FC<ChatPromptInputProps> = ({
  promptInput,
  setPromptInput,
  isGenerating,
  userRole,
  onSubmit,
}) => {
  return (
    <div className="p-3 sm:p-4 border-t border-dark-border bg-dark-surface/90 backdrop-blur-md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="max-w-4xl mx-auto relative flex items-center"
      >
        <input
          type="text"
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
          placeholder={`Pregunta a Datia sobre los datos corporativos (${userRole})...`}
          disabled={isGenerating}
          aria-label="Pregunta analítica"
          className="w-full bg-dark-base border border-dark-border rounded-2xl pl-4 sm:pl-5 pr-12 sm:pr-14 py-3 sm:py-3.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors shadow-inner"
        />

        <button
          type="submit"
          disabled={!promptInput.trim() || isGenerating}
          aria-label="Enviar consulta"
          className="absolute right-2 sm:right-2.5 p-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white disabled:opacity-40 disabled:pointer-events-none transition-colors shadow-md shadow-brand-600/30"
        >
          <Send className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </button>
      </form>
    </div>
  );
};
