import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Database, ShieldCheck, ChevronDown, Check, Cpu } from 'lucide-react';
import { CorporateConnection } from '../../features/admin/services/connector_service';

interface ChatPromptInputProps {
  promptInput: string;
  setPromptInput: (val: string) => void;
  isGenerating: boolean;
  userRole: string;
  activeDatabaseName?: string;
  activeConnectionId?: number | null;
  connectors?: CorporateConnection[];
  onSelectConnection?: (id: number) => void;
  onSubmit: () => void;
}

export const ChatPromptInput: React.FC<ChatPromptInputProps> = ({
  promptInput,
  setPromptInput,
  isGenerating,
  userRole,
  activeDatabaseName = 'BD Corporativa Local',
  activeConnectionId,
  connectors = [],
  onSelectConnection,
  onSubmit,
}) => {
  const [isDbDropdownOpen, setIsDbDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDbDropdownOpen(false);
      }
    };
    if (isDbDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDbDropdownOpen]);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [promptInput]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (promptInput.trim() && !isGenerating) {
        onSubmit();
      }
    }
  };

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-3 border border-white/10 shadow-2xl space-y-2.5 font-sans relative group transition-all">
      {/* Auto-resizing Textarea (Kokonut UI Style) */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={2}
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Consulta a DATIA en lenguaje natural (ej: 'Ventas de productos en Q3 por región')...`}
          disabled={isGenerating}
          aria-label="Pregunta analítica sobre datos corporativos"
          className="w-full bg-dark-base/80 text-xs sm:text-sm text-white placeholder-gray-500 rounded-xl px-3.5 py-2.5 resize-none focus:outline-none transition-colors scrollbar-thin scrollbar-thumb-dark-border font-sans leading-relaxed"
        />
      </div>

      {/* Kokonut UI Toolbar & Action Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 pt-1 border-t border-dark-border/60">
        {/* Left Toolbar Items: Active Database Selector & Model Pill */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Database Selector Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDbDropdownOpen((prev) => !prev)}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-xl bg-dark-base/90 hover:bg-dark-card border border-dark-border/80 text-[11px] font-medium text-gray-300 hover:text-white transition-all shadow-sm focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <Database className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span className="truncate max-w-[140px] sm:max-w-[180px] font-semibold">{activeDatabaseName}</span>
              <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform duration-200 ${isDbDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isDbDropdownOpen && connectors.length > 0 && (
              <div className="absolute left-0 bottom-full mb-2 w-64 rounded-2xl bg-dark-surface border border-dark-border shadow-2xl p-2 z-50 space-y-1 animate-fadeIn">
                <div className="px-2 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider border-b border-dark-border/60 mb-1">
                  Seleccionar Fuente de Datos
                </div>
                <div className="max-h-48 overflow-y-auto space-y-1 custom-scrollbar">
                  {connectors.map((c) => {
                    const isSelected = c.id === activeConnectionId;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          if (onSelectConnection) onSelectConnection(c.id);
                          setIsDbDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between p-2 rounded-xl text-xs text-left transition-colors ${
                          isSelected
                            ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 font-bold'
                            : 'text-gray-300 hover:bg-dark-card'
                        }`}
                      >
                        <div className="truncate min-w-0">
                          <div className="truncate font-semibold">{c.name}</div>
                          <div className="text-[9px] text-gray-500 font-mono uppercase">{c.db_type}</div>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-brand-400 shrink-0 ml-1" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* AI Model & Privacy Badge */}
          <span className="hidden sm:flex items-center space-x-1 px-2.5 py-1 rounded-xl bg-purple-500/10 border border-purple-500/20 text-[10px] text-purple-300 font-medium">
            <Cpu className="w-3 h-3 text-purple-400 shrink-0" />
            <span className="relative flex h-1.5 w-1.5 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            <span>IA Local (Text-to-SQL)</span>
          </span>

          {/* RBAC Badge */}
          <span className="hidden md:flex items-center space-x-1 text-[10px] text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-xl border border-indigo-500/20 font-medium">
            <ShieldCheck className="w-3 h-3 text-indigo-400 shrink-0" />
            <span>RBAC: {userRole}</span>
          </span>
        </div>

        {/* Right Action: Send Button (Kokonut UI Circular Glow Button) */}
        <div className="flex items-center space-x-2">
          <span className="hidden sm:inline text-[10px] text-gray-500">Enter ↵</span>
          <button
            type="button"
            onClick={() => {
              if (promptInput.trim() && !isGenerating) {
                onSubmit();
              }
            }}
            disabled={!promptInput.trim() || isGenerating}
            aria-label="Enviar consulta a DATIA"
            title="Enviar consulta"
            className="p-2.5 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white disabled:opacity-30 disabled:pointer-events-none transition-all shadow-md shadow-brand-600/30 glow-brand hover:scale-105"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
