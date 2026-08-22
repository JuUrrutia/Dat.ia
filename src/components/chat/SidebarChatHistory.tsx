import React from 'react';
import { Plus, MessageSquare, History, Trash2, X, Database } from 'lucide-react';

export interface ChatThread {
  id: string;
  title: string;
  timestamp: string;
}

interface SidebarChatHistoryProps {
  threads: ChatThread[];
  activeId: string | null;
  activeDatabaseName?: string;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  onSelectThread: (id: string) => void;
  onNewThread: () => void;
  onDeleteThread: (id: string, e: React.MouseEvent) => void;
}

export const SidebarChatHistory: React.FC<SidebarChatHistoryProps> = ({
  threads,
  activeId,
  activeDatabaseName = 'BD Corporativa Local (SQLite)',
  isOpenMobile = false,
  onCloseMobile,
  onSelectThread,
  onNewThread,
  onDeleteThread,
}) => {
  const sidebarContent = (
    <div className="w-72 bg-dark-surface/95 border-r border-dark-border flex flex-col h-full shrink-0 select-none">
      {/* New Query Button & Mobile Close Header */}
      <div className="p-3 sm:p-4 border-b border-dark-border/60 flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            onNewThread();
            if (onCloseMobile) onCloseMobile();
          }}
          className="flex-1 flex items-center justify-center space-x-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold py-2.5 px-4 rounded-xl shadow-lg shadow-brand-500/20 transition-colors group"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          <span>Nueva Consulta</span>
        </button>

        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Cerrar barra lateral"
            className="md:hidden p-2 rounded-xl text-gray-400 hover:text-white hover:bg-dark-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Threads List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <div>
          <div className="flex items-center space-x-1.5 px-2 mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
            <History className="w-3 h-3 text-brand-400" />
            <span>Historial de Consultas</span>
          </div>

          <div className="space-y-1">
            {threads.map((t) => {
              const isActive = t.id === activeId;
              return (
                <div
                  key={t.id}
                  className="group relative w-full flex items-center justify-between"
                >
                  <button
                    type="button"
                    onClick={() => {
                      onSelectThread(t.id);
                      if (onCloseMobile) onCloseMobile();
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs text-left transition-colors ${
                      isActive
                        ? 'bg-brand-500/15 text-white border border-brand-500/30 font-medium'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-dark-card/60 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 truncate pr-6">
                      <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-brand-400' : 'text-gray-500'}`} />
                      <span className="truncate">{t.title}</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={(e) => onDeleteThread(t.id, e)}
                    aria-label={`Eliminar conversación ${t.title}`}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-rose-400 transition-opacity absolute right-2"
                    title="Eliminar conversación"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}

            {threads.length === 0 && (
              <div className="text-center py-8 text-xs text-gray-500 px-2">
                No hay conversaciones previas. Haz clic en "Nueva Consulta" para iniciar una.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Database Active Status Footer */}
      <div className="p-3 border-t border-dark-border/60 bg-dark-base/40">
        <div className="flex items-center space-x-2.5 bg-dark-card/50 p-2.5 rounded-xl border border-dark-border">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <div className="truncate min-w-0">
            <div className="text-[10px] text-gray-400 uppercase font-semibold flex items-center gap-1">
              <Database className="w-2.5 h-2.5 text-brand-400" />
              <span>Fuente BD Activa</span>
            </div>
            <div className="text-[11px] text-gray-200 truncate font-mono font-medium">
              {activeDatabaseName}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden md:flex flex-col h-full shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Slide-over */}
      {isOpenMobile && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          {/* Backdrop */}
          <button
            type="button"
            aria-label="Cerrar barra lateral"
            className="fixed inset-0 w-full h-full bg-black/70 backdrop-blur-xs transition-opacity animate-fadeIn cursor-default focus:outline-none"
            onClick={onCloseMobile}
          />
          {/* Drawer content */}
          <div className="relative z-50 flex h-full animate-slideInLeft">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
