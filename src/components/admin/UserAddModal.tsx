import React, { useState } from 'react';
import { X, UserPlus, ShieldCheck } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { authService } from '../../features/auth/services/auth_service';
import { useModalA11y } from '../../hooks/useModalA11y';
import { resolveRoleLabel } from '../../constants';

interface UserAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (created: UserItem) => void;
}

export const UserAddModal: React.FC<UserAddModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Dialog semantics, Escape, focus containment and focus restore.
  const modalRef = useModalA11y<HTMLDivElement>(isOpen, onClose);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newPassword.trim()) {
      setCreateError('Por favor completa el nombre de usuario y contraseña.');
      return;
    }

    setIsSubmitting(true);
    setCreateError(null);

    try {
      // /auth/register is a PUBLIC self-registration endpoint: the backend
      // ignores the payload and decides el rol (o lo deja en null). Build the row
      // from what the server actually did — a synthetic id 404s the next
      // Edit/Sesiones/Reset call, and a role the account does not hold is worse
      // than saying que no tiene.
      const created = await authService.register({
        username: newUsername,
        email: newEmail || undefined,
        password: newPassword,
      });

      const createdItem: UserItem = {
        id: created.id,
        name: created.username,
        email: created.email || `${created.username}@empresa.com`,
        role: resolveRoleLabel(created),
        is_admin: created.is_admin,
      };

      setNewUsername('');
      setNewEmail('');
      setNewPassword('');
      setCreateError(null);
      onSuccess(createdItem);
      onClose();
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Error al registrar el nuevo usuario.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Registrar nuevo usuario" tabIndex={-1} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[88vh] sm:max-h-[90vh]">
        {/* Header */}
        <div className="shrink-0 px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <h4 className="text-sm font-bold text-app-text flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-purple-400" /> Registrar Nuevo Usuario
          </h4>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-app-text p-1 rounded-lg hover:bg-dark-card transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form id="user-add-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6 space-y-3.5 text-xs">
          {createError && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {createError}
            </div>
          )}

          <div>
            <label htmlFor="new-user-username" className="block text-gray-300 font-medium mb-1">
              Nombre de Usuario
            </label>
            <input
              id="new-user-username"
              aria-label="Nombre de Usuario"
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="ej. felipe_analista"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500"
              required
            />
          </div>

          <div>
            <label htmlFor="new-user-email" className="block text-gray-300 font-medium mb-1">
              Correo Electrónico
            </label>
            <input
              id="new-user-email"
              aria-label="Correo Electrónico"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="usuario@empresa.com"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500"
            />
          </div>

          <div>
            <label htmlFor="new-user-password" className="block text-gray-300 font-medium mb-1">
              Contraseña Inicial
            </label>
            <input
              id="new-user-password"
              aria-label="Contraseña Inicial"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500"
              required
            />
          </div>

          <div className="flex items-start space-x-2 text-[11px] text-gray-400 bg-dark-base/40 rounded-xl border border-dark-border/60 px-3 py-2.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
            <span>
              El registro es de mínimo privilegio: la cuenta nace con el perfil{' '}
              <strong className="text-app-text">Usuario</strong> y sin privilegios de
              administrador. Asigna su rol RBAC y sus permisos desde{' '}
              <strong className="text-app-text">Editar</strong> una vez creado.
            </span>
          </div>
        </form>

        {/* Fixed Sticky Footer Actions */}
        <div className="shrink-0 px-5 sm:px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex justify-end space-x-2 z-10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs hover:bg-dark-border transition-colors"
          >
            Cancelar
          </button>
          <button
            form="user-add-form"
            type="submit"
            disabled={isSubmitting}
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Registrando...' : 'Registrar'}
          </button>
        </div>
      </div>
    </div>
  );
};
