import React, { useEffect, useState } from 'react';
import { Keyboard, X } from 'lucide-react';
import { useModalA11y } from '../../hooks/useModalA11y';
import { KEYBOARD_SHORTCUTS, KeyboardShortcut } from '../../constants/help';

/** Evento para abrir el panel desde cualquier parte (ej. boton en /ayuda). */
export const OPEN_SHORTCUTS_EVENT = 'datia:open-shortcuts';

export const openKeyboardShortcuts = () => {
  window.dispatchEvent(new Event(OPEN_SHORTCUTS_EVENT));
};

/** No robar el "?" cuando el usuario esta escribiendo una pregunta. */
const isTypingTarget = (target: EventTarget | null): boolean => {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
};

export const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="inline-flex items-center justify-center min-w-[1.75rem] px-1.5 py-0.5 rounded-md border border-slate-300 dark:border-dark-border bg-slate-100 dark:bg-dark-base text-[11px] font-mono font-semibold text-slate-700 dark:text-gray-200 shadow-[0_1px_0_rgba(0,0,0,0.15)]">
    {children}
  </kbd>
);

export const ShortcutKeys: React.FC<{ shortcut: KeyboardShortcut }> = ({ shortcut }) => (
  <span className="flex items-center gap-1 shrink-0">
    {shortcut.keys.map((k, i) => (
      <React.Fragment key={k}>
        {i > 0 && <span className="text-[10px] text-gray-400">+</span>}
        <Kbd>{k}</Kbd>
      </React.Fragment>
    ))}
  </span>
);

/**
 * Panel global de atajos de teclado. Se abre con "?" en cualquier pantalla
 * protegida (fuera de campos de texto) o con `openKeyboardShortcuts()`.
 */
export const KeyboardShortcutsModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const close = () => setIsOpen(false);
  const modalRef = useModalA11y<HTMLDivElement>(isOpen, close);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== '?' || e.ctrlKey || e.metaKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      e.preventDefault();
      setIsOpen((prev) => !prev);
    };
    const onOpen = () => setIsOpen(true);
    window.addEventListener('keydown', onKey);
    window.addEventListener(OPEN_SHORTCUTS_EVENT, onOpen);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener(OPEN_SHORTCUTS_EVENT, onOpen);
    };
  }, []);

  if (!isOpen) return null;

  const scopes = Array.from(new Set(KEYBOARD_SHORTCUTS.map((s) => s.scope)));

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label="Atajos de teclado"
        tabIndex={-1}
        className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-5 shadow-2xl space-y-4"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-500">
              <Keyboard className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-gray-900 dark:text-white">Atajos de teclado</h2>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Cerrar atajos de teclado"
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-dark-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {scopes.map((scope) => (
          <div key={scope} className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{scope}</div>
            <ul className="space-y-1">
              {KEYBOARD_SHORTCUTS.filter((s) => s.scope === scope).map((s) => (
                <li
                  key={s.description}
                  className="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-slate-50 dark:bg-dark-base/60 border border-slate-200/70 dark:border-dark-border/60"
                >
                  <span className="text-xs text-slate-700 dark:text-gray-300">{s.description}</span>
                  <ShortcutKeys shortcut={s} />
                </li>
              ))}
            </ul>
          </div>
        ))}

        <p className="text-[11px] text-gray-400 text-center">
          En Mac usa <Kbd>⌘</Kbd> en lugar de <Kbd>Ctrl</Kbd>.
        </p>
      </div>
    </div>
  );
};
