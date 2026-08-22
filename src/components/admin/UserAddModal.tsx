import React, { useState } from 'react';
import { X, UserPlus } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { authService } from '../../services/auth_service';
import { CORPORATE_ROLES } from '../../constants';

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
  const [newRole, setNewRole] = useState('Analista Financiero & Comercial');
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      await authService.register({
        username: newUsername,
        email: newEmail || undefined,
        password: newPassword,
        is_admin: newIsAdmin,
      });

      const createdItem: UserItem = {
        id: Date.now(),
        name: newUsername,
        email: newEmail || `${newUsername}@empresa.com`,
        role: newRole,
        is_admin: newIsAdmin,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-purple-400" /> Registrar Nuevo Usuario
          </h4>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500"
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500"
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500"
              required
            />
          </div>

          <div>
            <label htmlFor="new-user-role" className="block text-gray-300 font-medium mb-1">
              Perfil Rol RBAC
            </label>
            <select
              id="new-user-role"
              aria-label="Perfil Rol RBAC"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 text-xs"
            >
              {CORPORATE_ROLES.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.label} — {r.description}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2 pt-1">
            <input
              type="checkbox"
              id="new-user-is-admin"
              aria-label="Otorgar Privilegios de Administrador"
              checked={newIsAdmin}
              onChange={(e) => setNewIsAdmin(e.target.checked)}
              className="w-4 h-4 text-purple-600 rounded bg-dark-base border-dark-border focus:ring-purple-500"
            />
            <label htmlFor="new-user-is-admin" className="text-gray-300 cursor-pointer">
              Otorgar Privilegios de Administrador
            </label>
          </div>

          <div className="pt-3 flex justify-end space-x-2 border-t border-dark-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs hover:bg-dark-border transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
            >
              {isSubmitting ? 'Registrando...' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
