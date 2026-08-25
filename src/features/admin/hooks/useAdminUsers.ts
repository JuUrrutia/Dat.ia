import { useReducer, useEffect } from 'react';
import { UserItem } from '../../../components/admin/AdminUsersTab';

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

export function useAdminUsers(users: UserItem[], onRefreshUsers?: () => void) {
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

  return {
    state,
    dispatch,
    filteredUsers,
    handleSaveRole,
    handleUserCreated,
  };
}
