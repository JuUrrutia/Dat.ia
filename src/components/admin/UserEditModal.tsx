import React, { useState, useEffect } from 'react';
import { X, Save, RefreshCw, AlertTriangle } from 'lucide-react';
import { UserItem } from './AdminUsersTab';
import { authService } from '../../features/auth/services/auth_service';
import { useModalA11y } from '../../hooks/useModalA11y';

interface UserEditModalProps {
  isOpen: boolean;
  user: UserItem | null;
  onClose: () => void;
  // Recibe el UserOut que devolvio el servidor, no los valores del formulario.
  // Si el backend respondio 200, lo que se muestra en la tabla es lo que la
  // base tiene.
  onSaved: (updated: UserItem) => void;
}

export const UserEditModal: React.FC<UserEditModalProps> = ({
  isOpen,
  user,
  onClose,
  onSaved,
}) => {
  const [selectedRole, setSelectedRole] = useState('');
  const [isAdminCheck, setIsAdminCheck] = useState(false);
  const [roles, setRoles] = useState<{ id: number; name: string; description: string }[]>([]);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // El catalogo de roles viene del servidor (`/auth/roles`). La constante
  // CORPORATE_ROLES del front tiene nombres que la base no tiene ("Economista"
  // vs "Analista Financiero & Comercial"), asi que un desplegable hardcodeado
  // hacia que el 400 "rol no existe" fuera la norma en vez de la excepcion.
  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setRolesError(null);
    authService
      .getAvailableRoles()
      .then((data) => {
        if (!cancelled) setRoles(Array.isArray(data) ? data : []);
      })
      .catch((err: any) => {
        if (!cancelled) {
          // Sin catalogo no se puede pintar un select honesto: se muestra el
          // error en vez de un dropdown con roles inventados.
          setRoles([]);
          setRolesError(err?.response?.data?.detail || 'No se pudo cargar el catálogo de roles del servidor.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => {
    if (user) {
      setSelectedRole(user.role);
      setIsAdminCheck(user.is_admin);
      setSubmitError(null);
    }
  }, [user]);

  // Dialog semantics, Escape, focus containment and focus restore.
  const modalRef = useModalA11y<HTMLDivElement>(isOpen, onClose);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRole) {
      setSubmitError('Selecciona un rol antes de guardar.');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const saved = await authService.updateUserRole(user.id, {
        role: selectedRole,
        is_admin: isAdminCheck,
      });
      onSaved({
        id: saved.id,
        name: saved.username,
        username: saved.username,
        email: saved.email || `${saved.username}@empresa.com`,
        role: saved.role_name || (saved.is_admin ? 'Administrador' : 'Usuario'),
        is_admin: saved.is_admin,
      });
      onClose();
    } catch (err: any) {
      setSubmitError(
        err?.response?.data?.detail ||
          'No se pudo actualizar el usuario en el servidor. El cambio no se aplicó.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Editar usuario" tabIndex={-1} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[88vh] sm:max-h-[90vh]">
        {/* Header */}
        <div className="shrink-0 px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <h4 className="text-sm font-bold text-app-text truncate">
            Editar Perfil & Gobernanza - {user.name}
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
        <form
          id="user-edit-form"
          onSubmit={handleSubmit}
          className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6 space-y-4 text-xs"
        >
          {rolesError && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{rolesError}</span>
            </div>
          )}

          {submitError && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{submitError}</span>
            </div>
          )}

          <div>
            <label htmlFor="edit-user-role" className="block font-medium text-gray-300 mb-1">
              Seleccionar Perfil RBAC
            </label>
            <select
              id="edit-user-role"
              aria-label="Seleccionar Perfil RBAC"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              disabled={Boolean(rolesError) || isSubmitting}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500 text-xs disabled:opacity-50"
            >
              {roles.map((r) => (
                <option key={r.id} value={r.name}>
                  {r.name}
                  {r.description ? ` — ${r.description}` : ''}
                </option>
              ))}
            </select>
            {roles.length === 0 && !rolesError && (
              <p className="mt-1 text-[11px] text-gray-500">Cargando catálogo de roles...</p>
            )}
          </div>

          <div className="flex items-center space-x-2 pt-1">
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
        </form>

        {/* Fixed Sticky Footer Actions */}
        <div className="shrink-0 px-5 sm:px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex justify-end space-x-2 z-10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
          >
            Cancelar
          </button>
          <button
            form="user-edit-form"
            type="submit"
            disabled={isSubmitting || Boolean(rolesError) || roles.length === 0}
            className="flex items-center space-x-1 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Guardando...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Guardar Rol</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};