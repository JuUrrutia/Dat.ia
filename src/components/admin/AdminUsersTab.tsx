import React, { useReducer, useEffect } from 'react';
import { Users, UserPlus, Search, ShieldCheck, Edit3, Check, Monitor, KeyRound } from 'lucide-react';
import { UserEditModal } from './UserEditModal';
import { UserAddModal } from './UserAddModal';
import { UserSessionsModal } from './UserSessionsModal';
import { UserPasswordResetModal } from './UserPasswordResetModal';

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
  onRefreshUsers?: () => void;
}

interface UsersState {
  userList: UserItem[];
  searchQuery: string;
  editingUser: UserItem | null;
  sessionsUser: UserItem | null;
  resetPasswordUser: UserItem | null;
  isNewUserModalOpen: boolean;
  isSuccessBanner: string | null;
}

type UsersAction =
  | { type: 'SET_USER_LIST'; users: UserItem[] }
  | { type: 'SET_SEARCH'; query: string }
  | { type: 'OPEN_EDIT'; user: UserItem }
  | { type: 'CLOSE_EDIT' }
  | { type: 'OPEN_SESSIONS'; user: UserItem }
  | { type: 'CLOSE_SESSIONS' }
  | { type: 'OPEN_RESET_PASSWORD'; user: UserItem }
  | { type: 'CLOSE_RESET_PASSWORD' }
  | { type: 'OPEN_NEW_USER' }
  | { type: 'CLOSE_NEW_USER' }
  | { type: 'SET_SUCCESS_BANNER'; message: string | null };

import { getRoleBadgeStyle } from '../../constants';

const STORAGE_KEY = 'datia_governance_users:v1';
const LEGACY_STORAGE_KEY = 'datia_governance_users';

function usersReducer(state: UsersState, action: UsersAction): UsersState {
  switch (action.type) {
    case 'SET_USER_LIST':
      return { ...state, userList: action.users };
    case 'SET_SEARCH':
      return { ...state, searchQuery: action.query };
    case 'OPEN_EDIT':
      return { ...state, editingUser: action.user };
    case 'CLOSE_EDIT':
      return { ...state, editingUser: null };
    case 'OPEN_SESSIONS':
      return { ...state, sessionsUser: action.user };
    case 'CLOSE_SESSIONS':
      return { ...state, sessionsUser: null };
    case 'OPEN_RESET_PASSWORD':
      return { ...state, resetPasswordUser: action.user };
    case 'CLOSE_RESET_PASSWORD':
      return { ...state, resetPasswordUser: null };
    case 'OPEN_NEW_USER':
      return { ...state, isNewUserModalOpen: true };
    case 'CLOSE_NEW_USER':
      return { ...state, isNewUserModalOpen: false };
    case 'SET_SUCCESS_BANNER':
      return { ...state, isSuccessBanner: action.message };
    default:
      return state;
  }
}

export const AdminUsersTab: React.FC<AdminUsersTabProps> = ({ users, onRefreshUsers }) => {
  const [state, dispatch] = useReducer(usersReducer, {
    userList: users,
    searchQuery: '',
    editingUser: null,
    sessionsUser: null,
    resetPasswordUser: null,
    isNewUserModalOpen: false,
    isSuccessBanner: null,
  });

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
      if (stored) {
        dispatch({ type: 'SET_USER_LIST', users: JSON.parse(stored) });
      } else {
        dispatch({ type: 'SET_USER_LIST', users });
      }
    } catch {
      dispatch({ type: 'SET_USER_LIST', users });
    }
  }, [users]);

  const saveUsersToStorage = (updated: UserItem[]) => {
    dispatch({ type: 'SET_USER_LIST', users: updated });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Ignore quota error
    }
  };

  const filteredUsers = state.userList.filter(
    (u) =>
      u.name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      u.role.toLowerCase().includes(state.searchQuery.toLowerCase())
  );

  const handleSaveRole = (role: string, isAdmin: boolean) => {
    if (!state.editingUser) return;
    const editingUser = state.editingUser;

    const updated = state.userList.map((u) => {
      if (u.id === editingUser.id) {
        return {
          ...u,
          role,
          is_admin: isAdmin,
        };
      }
      return u;
    });

    saveUsersToStorage(updated);
    dispatch({
      type: 'SET_SUCCESS_BANNER',
      message: `Rol actualizado exitosamente para ${editingUser.name} -> ${role}`,
    });
    dispatch({ type: 'CLOSE_EDIT' });
    setTimeout(() => dispatch({ type: 'SET_SUCCESS_BANNER', message: null }), 3500);
  };

  const handleUserCreated = (createdItem: UserItem) => {
    const updatedUsers = [...state.userList, createdItem];
    saveUsersToStorage(updatedUsers);
    dispatch({
      type: 'SET_SUCCESS_BANNER',
      message: `Usuario '${createdItem.name}' registrado correctamente.`,
    });
    if (onRefreshUsers) onRefreshUsers();
    setTimeout(() => dispatch({ type: 'SET_SUCCESS_BANNER', message: null }), 3500);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-purple-400" /> Matriz de Usuarios y Gobernanza RBAC
          </h3>
          <p className="text-xs text-gray-400">
            Asignación de perfiles (Administrador, Economista, TI, Usuario), control de sesiones y reseteo de claves
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
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
              className="bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          <button
            type="button"
            onClick={() => dispatch({ type: 'OPEN_NEW_USER' })}
            className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            <span>Registrar Usuario</span>
          </button>
        </div>
      </div>

      {state.isSuccessBanner && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4 shrink-0" />
          <span>{state.isSuccessBanner}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-dark-base border-b border-dark-border text-gray-400 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Correo</th>
              <th className="px-4 py-3">Rol RBAC Asignado</th>
              <th className="px-4 py-3">Privilegios Admin</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border text-gray-200">
            {filteredUsers.map((u) => (
              <tr key={u.id} className="hover:bg-dark-card/50 transition-colors">
                <td className="px-4 py-3 font-medium text-white flex items-center space-x-2">
                  <span className="w-7 h-7 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 font-bold text-xs flex items-center justify-center">
                    {u.name.charAt(0).toUpperCase()}
                  </span>
                  <div>
                    <span>{u.name}</span>
                    {u.username && u.username !== u.name && (
                      <p className="text-[10px] text-gray-500">@{u.username}</p>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-400 font-mono">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`border px-2.5 py-1 rounded-lg text-xs font-semibold ${getRoleBadgeStyle(u.role)}`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.is_admin ? (
                    <span className="inline-flex items-center space-x-1 text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded text-[11px]">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Super Admin</span>
                    </span>
                  ) : (
                    <span className="text-gray-500">Estándar</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end space-x-1.5">
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_SESSIONS', user: u })}
                      aria-label={`Ver sesiones de ${u.name}`}
                      title="Ver sesiones activas"
                      className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <Monitor className="w-3.5 h-3.5" />
                      <span>Sesiones</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_RESET_PASSWORD', user: u })}
                      aria-label={`Resetear contraseña de ${u.name}`}
                      title="Resetear contraseña"
                      className="flex items-center space-x-1 text-xs text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Reset Clave</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: 'OPEN_EDIT', user: u })}
                      aria-label={`Editar rol para ${u.name}`}
                      className="flex items-center space-x-1 text-xs text-purple-400 hover:text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Editar Rol</span>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit Role Modal */}
      <UserEditModal
        isOpen={Boolean(state.editingUser)}
        user={state.editingUser}
        onClose={() => dispatch({ type: 'CLOSE_EDIT' })}
        onSave={handleSaveRole}
      />

      {/* User Sessions Modal */}
      <UserSessionsModal
        isOpen={Boolean(state.sessionsUser)}
        user={state.sessionsUser}
        onClose={() => dispatch({ type: 'CLOSE_SESSIONS' })}
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
