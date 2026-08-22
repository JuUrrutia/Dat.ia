import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { CORPORATE_ROLES } from '../../constants';

interface UserEditModalProps {
  isOpen: boolean;
  user: UserItem | null;
  onClose: () => void;
  onSave: (role: string, isAdmin: boolean) => void;
}

export const UserEditModal: React.FC<UserEditModalProps> = ({
  isOpen,
  user,
  onClose,
  onSave,
}) => {
  const [selectedRole, setSelectedRole] = useState('Analista Financiero & Comercial');
  const [isAdminCheck, setIsAdminCheck] = useState(false);

  useEffect(() => {
    if (user) {
      setSelectedRole(user.role);
      setIsAdminCheck(user.is_admin);
    }
  }, [user]);

  if (!isOpen || !user) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(selectedRole, isAdminCheck);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <h4 className="text-sm font-bold text-white">
            Editar Perfil & Gobernanza - {user.name}
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
          <div>
            <label htmlFor="edit-user-role" className="block font-medium text-gray-300 mb-1">
              Seleccionar Perfil RBAC
            </label>
            <select
              id="edit-user-role"
              aria-label="Seleccionar Perfil RBAC"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 text-xs"
            >
              {CORPORATE_ROLES.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.label} — {r.description}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2 pt-2">
            <input
              type="checkbox"
              id="edit-user-is-admin"
              aria-label="Otorgar Privilegios de Super Administrador"
              checked={isAdminCheck}
              onChange={(e) => setIsAdminCheck(e.target.checked)}
              className="w-4 h-4 text-purple-600 rounded bg-dark-base border-dark-border focus:ring-purple-500"
            />
            <label htmlFor="edit-user-is-admin" className="text-gray-300 font-medium cursor-pointer">
              Otorgar Privilegios de Super Administrador
            </label>
          </div>

          <div className="pt-3 flex justify-end space-x-2 border-t border-dark-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex items-center space-x-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Guardar Rol</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
