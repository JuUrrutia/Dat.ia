import React, { useState, useEffect, useCallback } from 'react';
import { X, ShieldAlert, Monitor, Clock, AlertTriangle, RefreshCw } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { authService } from '../../services/auth_service';
import { UserSession } from '../../types';

interface UserSessionsModalProps {
  isOpen: boolean;
  user: UserItem | null;
  onClose: () => void;
}

export const UserSessionsModal: React.FC<UserSessionsModalProps> = ({
  isOpen,
  user,
  onClose,
}) => {
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadSessions = useCallback(async (userId: number) => {
    setLoading(true);
    setMsg(null);
    try {
      const data = await authService.getUserSessions(userId);
      setSessions(data);
    } catch {
      setMsg({ type: 'error', text: 'No se pudieron cargar las sesiones activas.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    if (isOpen && user) {
      authService.getUserSessions(user.id)
        .then((data) => {
          if (!ignore) {
            setSessions(data);
            setLoading(false);
          }
        })
        .catch(() => {
          if (!ignore) {
            setMsg({ type: 'error', text: 'No se pudieron cargar las sesiones activas.' });
            setLoading(false);
          }
        });
    }

    return () => {
      ignore = true;
    };
  }, [isOpen, user]);

  if (!isOpen || !user) return null;

  const handleRevokeSingle = async (sessionId: number) => {
    setActionLoading(true);
    try {
      await authService.revokeSession(sessionId);
      setMsg({ type: 'success', text: 'Sesión revocada exitosamente.' });
      await loadSessions(user.id);
    } catch {
      setMsg({ type: 'error', text: 'Error al revocar la sesión seleccionada.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeAll = async () => {
    if (!window.confirm(`¿Estás seguro de cerrar todas las sesiones activas de ${user.name}?`)) {
      return;
    }
    setActionLoading(true);
    try {
      const res = await authService.revokeAllUserSessions(user.id);
      setMsg({ type: 'success', text: res.message || 'Todas las sesiones fueron revocadas.' });
      await loadSessions(user.id);
    } catch {
      setMsg({ type: 'error', text: 'Error al revocar todas las sesiones.' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-xl rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2">
            <Monitor className="w-5 h-5 text-indigo-400" />
            <div>
              <h4 className="text-sm font-bold text-white">
                Sesiones Activas - {user.name}
              </h4>
              <p className="text-xs text-gray-400">@{user.username} ({user.role})</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal de sesiones"
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {msg && (
          <div
            className={`p-3 rounded-xl text-xs flex items-center space-x-2 ${
              msg.type === 'success'
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
            }`}
          >
            {msg.type === 'success' ? (
              <ShieldAlert className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{msg.text}</span>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 font-medium">
              Dispositivos y clientes con acceso activo:
            </span>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => loadSessions(user.id)}
                disabled={loading || actionLoading}
                aria-label="Refrescar lista de sesiones"
                className="p-1.5 rounded-lg bg-dark-card hover:bg-dark-border text-gray-400 hover:text-white transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              {sessions.length > 0 && (
                <button
                  type="button"
                  onClick={handleRevokeAll}
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-semibold transition-colors flex items-center space-x-1"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Cerrar Todas</span>
                </button>
              )}
            </div>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-gray-400 flex items-center justify-center space-x-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Cargando sesiones...</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-400 bg-dark-base/40 rounded-xl border border-dark-border">
              No hay sesiones activas registradas para este usuario.
            </div>
          ) : (
            <div className="max-h-60 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="p-3 rounded-xl bg-dark-base border border-dark-border flex items-center justify-between space-x-3 text-xs"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-medium text-white">{s.ip_address || '127.0.0.1'}</span>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                        Activa
                      </span>
                    </div>
                    <p className="text-gray-400 text-[11px] truncate max-w-sm" title={s.user_agent}>
                      {s.user_agent || 'Cliente Desktop / Local'}
                    </p>
                    <div className="flex items-center space-x-3 text-[10px] text-gray-500">
                      <span className="flex items-center space-x-1">
                        <Clock className="w-3 h-3" />
                        <span>Inició: {new Date(s.created_at).toLocaleString()}</span>
                      </span>
                      <span>•</span>
                      <span>Último uso: {new Date(s.last_seen_at).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRevokeSingle(s.id)}
                    disabled={actionLoading}
                    aria-label={`Revocar sesión ID ${s.id}`}
                    className="px-2.5 py-1.5 rounded-lg bg-dark-card hover:bg-rose-500/20 text-gray-400 hover:text-rose-300 border border-dark-border hover:border-rose-500/30 text-[11px] font-medium transition-colors shrink-0"
                  >
                    Revocar
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-3 flex justify-end border-t border-dark-border">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
