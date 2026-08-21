import React, { useState } from 'react';
import { X, KeyRound, Copy, Check, AlertTriangle, RefreshCw } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { authService } from '../../services/auth_service';
import { PasswordResetResult } from '../../types';

interface UserPasswordResetModalProps {
  isOpen: boolean;
  user: UserItem | null;
  onClose: () => void;
}

export const UserPasswordResetModal: React.FC<UserPasswordResetModalProps> = ({
  isOpen,
  user,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PasswordResetResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen || !user) return null;

  const handleReset = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await authService.resetUserPassword(user.id);
      setResult(data);
    } catch {
      setError('No se pudo restablecer la contraseña. Verifica permisos de administrador.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (result?.temporary_password) {
      navigator.clipboard.writeText(result.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleModalClose = () => {
    setResult(null);
    setError(null);
    setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2">
            <KeyRound className="w-5 h-5 text-amber-400" />
            <div>
              <h4 className="text-sm font-bold text-white">
                Restablecer Contraseña
              </h4>
              <p className="text-xs text-gray-400">{user.name} (@{user.username})</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleModalClose}
            aria-label="Cerrar modal de reset de contraseña"
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!result ? (
          <div className="space-y-4 text-xs">
            <p className="text-gray-300 leading-relaxed">
              Esta acción generará una <strong className="text-white">contraseña temporal aleatoria</strong>,
              cerrará todas las sesiones activas de <strong className="text-white">{user.name}</strong> y le exigirá
              cambiar su contraseña de forma obligatoria en el próximo inicio de sesión.
            </p>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                Como Datia es un sistema 100% local y offline, deberás comunicar manualmente la clave temporal al usuario.
              </span>
            </div>

            <div className="pt-3 flex justify-end space-x-2 border-t border-dark-border">
              <button
                type="button"
                onClick={handleModalClose}
                disabled={loading}
                className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleReset}
                disabled={loading}
                className="flex items-center space-x-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-lg shadow-amber-600/20"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Generando clave...</span>
                  </>
                ) : (
                  <>
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>Generar Contraseña Temporal</span>
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
              Contraseña restablecida exitosamente. Entrégale esta clave provisional al usuario:
            </div>

            <div className="p-4 rounded-xl bg-dark-base border border-dark-border flex items-center justify-between space-x-3">
              <div className="space-y-1">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
                  Contraseña Temporal
                </span>
                <p className="font-mono text-sm font-bold text-amber-400 select-all">
                  {result.temporary_password}
                </p>
              </div>
              <button
                type="button"
                onClick={handleCopy}
                aria-label="Copiar contraseña temporal al portapapeles"
                className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-dark-card hover:bg-dark-border text-white text-xs font-medium transition-colors border border-dark-border"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copiada</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copiar</span>
                  </>
                )}
              </button>
            </div>

            <p className="text-[11px] text-gray-400 italic">
              Esta clave solo se mostrará una vez. Al cerrar esta ventana no se podrá volver a consultar.
            </p>

            <div className="pt-3 flex justify-end border-t border-dark-border">
              <button
                type="button"
                onClick={handleModalClose}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition-colors"
              >
                Entendido y Cerrar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
