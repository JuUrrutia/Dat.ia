import React, { useState } from 'react';
import { ShieldAlert, KeyRound, Check, AlertTriangle, RefreshCw } from 'lucide-react';
import { authService } from '../../services/auth_service';

interface MandatoryPasswordChangeModalProps {
  isOpen: boolean;
  onSuccess: () => void;
}

export const MandatoryPasswordChangeModal: React.FC<MandatoryPasswordChangeModalProps> = ({
  isOpen,
  onSuccess,
}) => {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!oldPassword.trim()) {
      setError('Debes ingresar tu contraseña actual o temporal.');
      return;
    }

    if (newPassword.length < 6) {
      setError('La nueva contraseña debe tener al menos 6 caracteres.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Las nuevas contraseñas no coinciden.');
      return;
    }

    if (oldPassword === newPassword) {
      setError('La nueva contraseña debe ser diferente a la actual.');
      return;
    }

    setLoading(true);
    try {
      await authService.changePassword(oldPassword, newPassword);
      onSuccess();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error al actualizar la contraseña. Verifica tu clave actual.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-amber-500/30 p-6 space-y-4 shadow-2xl shadow-amber-500/10">
        <div className="flex items-center space-x-3 border-b border-dark-border pb-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">
              Cambio de Contraseña Obligatorio
            </h4>
            <p className="text-xs text-gray-400">Política de Gobernanza y Seguridad</p>
          </div>
        </div>

        <p className="text-xs text-gray-300 leading-relaxed">
          Tu cuenta tiene asignada una clave provisional o se ha solicitado el cambio forzado de contraseña.
          Debes definir una nueva clave para continuar utilizando la plataforma.
        </p>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div>
            <label htmlFor="mandatory-old-pwd" className="block font-medium text-gray-300 mb-1">
              Contraseña Actual o Temporal
            </label>
            <input
              id="mandatory-old-pwd"
              aria-label="Contraseña Actual o Temporal"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="Ingresa la clave provisional..."
              required
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label htmlFor="mandatory-new-pwd" className="block font-medium text-gray-300 mb-1">
              Nueva Contraseña (mínimo 6 caracteres)
            </label>
            <input
              id="mandatory-new-pwd"
              aria-label="Nueva Contraseña"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Crea una contraseña segura..."
              required
              minLength={6}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label htmlFor="mandatory-confirm-pwd" className="block font-medium text-gray-300 mb-1">
              Confirmar Nueva Contraseña
            </label>
            <input
              id="mandatory-confirm-pwd"
              aria-label="Confirmar Nueva Contraseña"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repite la nueva contraseña..."
              required
              minLength={6}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="pt-3 border-t border-dark-border flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white text-xs font-semibold py-2.5 rounded-xl transition-colors shadow-lg shadow-amber-600/20"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Actualizando clave...</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-4 h-4" />
                  <span>Establecer Nueva Contraseña</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
