import React from 'react';
import { Plus, MessageSquare, History, Trash2 } from 'lucide-react';

export interface ChatThread {
  id: string;
  title: string;
  timestamp: string;
}

interface SidebarChatHistoryProps {
  threads: ChatThread[];
  activeId: string | null;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
  onDeleteThread: (id: string, e: React.MouseEvent) => void;
}

export const SidebarChatHistory: React.FC<SidebarChatHistoryProps> = ({
  threads,
  activeId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
}) => {
  return (
    <aside className="w-72 bg-dark-surface/90 border-r border-dark-border flex flex-col h-full shrink-0 select-none">
      {/* New Query Button */}
      <div className="p-4 border-b border-dark-border/60">
        <button
          onClick={onNewThread}
          className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold py-2.5 px-4 rounded-xl shadow-lg shadow-brand-500/20 transition-all group"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          <span>Nueva Consulta</span>
        </button>
      </div>

      {/* Threads List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <div>
          <div className="flex items-center space-x-1.5 px-2 mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
            <History className="w-3 h-3 text-brand-400" />
            <span>Historial de Conversaciones</span>
          </div>

          <div className="space-y-1">
            {threads.map((t) => {
              const isActive = t.id === activeId;
              return (
                <div
                  key={t.id}
                  onClick={() => onSelectThread(t.id)}
                  className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                    isActive
                      ? 'bg-brand-500/15 text-white border border-brand-500/30 font-medium'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-dark-card/60 border border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate pr-6">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-400' : 'text-gray-500'}`} />
                    <span className="truncate">{t.title}</span>
                  </div>

                  <button
                    onClick={(e) => onDeleteThread(t.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 transition-opacity absolute right-2"
                    title="Eliminar conversación"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}

            {threads.length === 0 && (
              <div className="text-center py-8 text-xs text-gray-500">
                No hay conversaciones previas. Haz clic en "Nueva Consulta" para iniciar una.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Database Active Status Footer */}
      <div className="p-3 border-t border-dark-border/60 bg-dark-base/40">
        <div className="flex items-center space-x-2 bg-dark-card/40 p-2.5 rounded-xl border border-dark-border">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <div className="truncate">
            <div className="text-[10px] text-gray-400 uppercase font-semibold">Fuente BD Activa</div>
            <div className="text-xs text-gray-200 truncate font-mono">BD_FINANZAS_PROD (Postgres)</div>
          </div>
        </div>
      </div>
    </aside>
  );
};
