import React, { useState } from 'react';
import { ShieldAlert, KeyRound, AlertTriangle, RefreshCw, LogOut, Eye, EyeOff } from 'lucide-react';
import { authService } from '../../features/auth/services/auth_service';
import { useModalA11y } from '../../hooks/useModalA11y';

interface MandatoryPasswordChangeModalProps {
  isOpen: boolean;
  onSuccess: () => void;
  onCancel?: () => void;
}

export const MandatoryPasswordChangeModal: React.FC<MandatoryPasswordChangeModalProps> = ({
  isOpen,
  onSuccess,
  onCancel,
}) => {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // One toggle for all three: confirming a new password means comparing the
  // last two, which needs both visible at the same time.
  const [showPasswords, setShowPasswords] = useState(false);

  // Dialog semantics, Escape, focus containment and focus restore.
  const modalRef = useModalA11y<HTMLDivElement>(isOpen, onCancel);

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
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Cambio de contraseña obligatorio" tabIndex={-1} className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-amber-500/30 p-6 space-y-4 shadow-2xl shadow-amber-500/10">
        <div className="flex items-center space-x-3 border-b border-dark-border pb-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-app-text">
              Cambio de Contraseña Obligatorio
            </h4>
            <p className="text-xs text-gray-400">Política de Gobernanza y Seguridad</p>
          </div>
        </div>

        <p className="text-xs text-gray-300 leading-relaxed">
          Tu cuenta tiene asignada una clave provisional o se ha solicitado el cambio forzado de contraseña.
          Debes definir una nueva clave para continuar utilizando la plataforma.
        </p>

        {/*
          Sin esto el modal es una caja sin salida: el overlay es `inset-0 z-[100]`
          y el logout del Header esta en `z-30`, o sea debajo. Sin refresh del token
          tampoco se escapa. Cerrar sesion es la unica salida y tiene que existir.
        */}
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-app-text transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Salir de mi cuenta</span>
          </button>
        )}

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
              name="currentPassword"
              autoComplete="current-password"
              type={showPasswords ? 'text' : 'password'}
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="Ingresa la clave provisional..."
              required
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-amber-500"
            />
            <button
              type="button"
              onClick={() => setShowPasswords((v) => !v)}
              aria-label={showPasswords ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}
              className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-app-text transition-colors"
            >
              {showPasswords ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              <span>{showPasswords ? 'Ocultar' : 'Mostrar'} contraseñas</span>
            </button>
          </div>

          <div>
            <label htmlFor="mandatory-new-pwd" className="block font-medium text-gray-300 mb-1">
              Nueva Contraseña (mínimo 6 caracteres)
            </label>
            <input
              id="mandatory-new-pwd"
              aria-label="Nueva Contraseña"
              name="newPassword"
              autoComplete="new-password"
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Crea una contraseña segura..."
              required
              minLength={6}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-amber-500"
            />
          </div>

          <div>
            <label htmlFor="mandatory-confirm-pwd" className="block font-medium text-gray-300 mb-1">
              Confirmar Nueva Contraseña
            </label>
            <input
              id="mandatory-confirm-pwd"
              aria-label="Confirmar Nueva Contraseña"
              name="confirmPassword"
              autoComplete="new-password"
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repite la nueva contraseña..."
              required
              minLength={6}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-amber-500"
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
