import React from 'react';
import { Users, UserPlus, Search, ShieldCheck, Check, Monitor, KeyRound, Pencil, RefreshCw } from 'lucide-react';
import { UserAddModal } from './UserAddModal';
import { UserSessionsModal } from './UserSessionsModal';
import { UserPasswordResetModal } from './UserPasswordResetModal';
import { UserEditModal } from './UserEditModal';
import { useAdminUsers } from '../../features/admin/hooks/useAdminUsers';
import { getRoleBadgeStyle } from '../../constants';

export interface UserItem {
  id: number;
  name: string;
  username?: string;
  email: string;
  role: string;
  is_admin: boolean;
}

interface AdminUsersTabProps {
  users: UserItem[];
  usersLoaded: boolean;
  onRefreshUsers?: () => void;
}

export const AdminUsersTab: React.FC<AdminUsersTabProps> = ({ users, usersLoaded, onRefreshUsers }) => {
  const {
    state,
    dispatch,
    filteredUsers,
    handleUserCreated,
    handleUserSaved,
  } = useAdminUsers(users, usersLoaded, onRefreshUsers);

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-200 dark:border-white/10 space-y-5 bg-white dark:bg-zinc-900/90 shadow-sm">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-brand-600 dark:text-purple-400" /> Matriz de Usuarios y Gobernanza RBAC
          </h3>
          <p className="text-xs text-slate-600 dark:text-gray-400">
            Asignación de perfiles (Administrador, Economista, TI, Usuario), control de sesiones y reseteo de claves
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-gray-400" />
            <label htmlFor="admin-users-search" className="sr-only">
              Buscar usuario o rol
            </label>
            <input
              id="admin-users-search"
              aria-label="Buscar usuario o rol"
              type="text"
              value={state.searchQuery}
              onChange={(e) => dispatch({ type: 'SET_SEARCH', query: e.target.value })}
              placeholder="Buscar usuario o rol..."
              className="bg-slate-50 dark:bg-dark-base border border-slate-300 dark:border-dark-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-gray-500 focus:outline-none focus:border-brand-500 shadow-xs"
            />
          </div>

          <button
            type="button"
            onClick={() => dispatch({ type: 'OPEN_NEW_USER' })}
            className="flex items-center space-x-1.5 text-xs bg-brand-600 hover:bg-brand-500 text-white font-medium px-4 py-2 rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <UserPlus className="w-4 h-4" />
            <span>Registrar Usuario</span>
          </button>
        </div>
      </div>

      {state.isSuccessBanner && (
        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4 shrink-0" />
          <span>{state.isSuccessBanner}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-dark-base border-b border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Correo</th>
              <th className="px-4 py-3">Rol RBAC Asignado</th>
              <th className="px-4 py-3">Privilegios Admin</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-dark-border text-slate-800 dark:text-gray-200 bg-white dark:bg-transparent">
            {!usersLoaded ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-600 dark:text-gray-400">
                  <div className="flex items-center justify-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-brand-600 dark:text-purple-400" />
                    <span>Cargando usuarios...</span>
                  </div>
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-500 dark:text-gray-400 space-y-3">
                  <p>No hay usuarios registrados.</p>
                  {onRefreshUsers && (
                    <button
                      type="button"
                      onClick={onRefreshUsers}
                      className="inline-flex items-center space-x-1.5 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-dark-card dark:hover:bg-dark-border text-slate-700 hover:text-slate-900 dark:text-gray-300 dark:hover:text-white border border-slate-200 dark:border-dark-border rounded-xl px-3 py-1.5 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Reintentar</span>
                    </button>
                  )}
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-500 dark:text-gray-400">
                  Ningún usuario coincide con «{state.searchQuery}».
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-dark-card/50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                  <div className="flex items-center space-x-2">
                  <span className="w-7 h-7 rounded-full bg-brand-50 border border-brand-200 text-brand-700 dark:bg-purple-500/20 dark:border-purple-500/30 dark:text-purple-300 font-bold text-xs flex items-center justify-center">
                    {u.name.charAt(0).toUpperCase()}
                  </span>
                  <div>
                    <span>{u.name}</span>
                    {u.username && u.username !== u.name && (
                      <p className="text-[10px] text-slate-500 dark:text-gray-500">@{u.username}</p>
                    )}
                  </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-600 dark:text-gray-400 font-mono">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`border px-2.5 py-1 rounded-lg text-xs font-semibold ${getRoleBadgeStyle(u.role)}`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.is_admin ? (
                    <span className="inline-flex items-center space-x-1 text-brand-700 bg-brand-50 border border-brand-200 dark:text-purple-400 dark:bg-purple-500/10 dark:border-purple-500/20 px-2 py-0.5 rounded text-[11px] font-semibold">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Super Admin</span>
                    </span>
                  ) : (
                    <span className="text-slate-500 dark:text-gray-500">Estándar</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end space-x-1.5">
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_EDIT', user: u })}
                      aria-label={`Editar rol de ${u.name}`}
                      title="Editar rol y privilegios"
                      className="flex items-center space-x-1 text-xs text-purple-700 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300 bg-purple-50 dark:bg-purple-500/10 hover:bg-purple-100 dark:hover:bg-purple-500/20 border border-purple-200 dark:border-purple-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      <span>Editar Rol</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_SESSIONS', user: u })}
                      aria-label={`Ver sesiones de ${u.name}`}
                      title="Ver sesiones activas"
                      className="flex items-center space-x-1 text-xs text-indigo-700 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 border border-indigo-200 dark:border-indigo-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <Monitor className="w-3.5 h-3.5" />
                      <span>Sesiones</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_RESET_PASSWORD', user: u })}
                      aria-label={`Resetear contraseña de ${u.name}`}
                      title="Resetear contraseña"
                      className="flex items-center space-x-1 text-xs text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-300 bg-amber-50 dark:bg-amber-500/10 hover:bg-amber-100 dark:hover:bg-amber-500/20 border border-amber-200 dark:border-amber-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Reset Clave</span>
                    </button>
                  </div>
                </td>
              </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* User Sessions Modal */}
      <UserSessionsModal
        isOpen={Boolean(state.sessionsUser)}
        user={state.sessionsUser}
        onClose={() => dispatch({ type: 'CLOSE_SESSIONS' })}
      />

      {/* User Role Edit Modal */}
      <UserEditModal
        isOpen={Boolean(state.editUser)}
        user={state.editUser}
        onClose={() => dispatch({ type: 'CLOSE_EDIT' })}
        onSaved={handleUserSaved}
      />

      {/* User Password Reset Modal */}
      <UserPasswordResetModal
        isOpen={Boolean(state.resetPasswordUser)}
        user={state.resetPasswordUser}
        onClose={() => dispatch({ type: 'CLOSE_RESET_PASSWORD' })}
      />

      {/* New User Modal */}
      <UserAddModal
        isOpen={state.isNewUserModalOpen}
        onClose={() => dispatch({ type: 'CLOSE_NEW_USER' })}
        onSuccess={handleUserCreated}
      />
    </div>
  );
};
