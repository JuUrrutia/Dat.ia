import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, X } from 'lucide-react';
import { useNotifications } from '../../context/NotificationContext';
import { ToastNotification, ToastType } from '../../types';

const getToastStyle = (type: ToastType) => {
  switch (type) {
    case 'success':
      return {
        bg: 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200 shadow-emerald-950/50',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
      };
    case 'warning':
      return {
        bg: 'bg-amber-950/90 border-amber-500/30 text-amber-200 shadow-amber-950/50',
        icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
      };
    case 'error':
      return {
        bg: 'bg-rose-950/90 border-rose-500/30 text-rose-200 shadow-rose-950/50',
        icon: <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
      };
    case 'info':
    default:
      return {
        bg: 'bg-indigo-950/90 border-indigo-500/30 text-indigo-200 shadow-indigo-950/50',
        icon: <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />,
      };
  }
};

const ToastItem: React.FC<{ toast: ToastNotification; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  const style = getToastStyle(toast.type);

  return (
    <div
      className={`pointer-events-auto flex items-start space-x-3 p-3.5 rounded-2xl border backdrop-blur-md shadow-2xl transition-all animate-fadeIn text-xs ${style.bg}`}
      role="alert"
    >
      {style.icon}
      <div className="flex-1 leading-relaxed font-medium pr-1">{toast.message}</div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Cerrar notificación"
        className="text-white/60 hover:text-white p-0.5 rounded-lg hover:bg-white/10 transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

export const ToastContainer: React.FC = () => {
  const { toasts, dismiss } = useNotifications();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed top-5 right-5 z-[120] flex flex-col space-y-2.5 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
      ))}
    </div>
  );
};
