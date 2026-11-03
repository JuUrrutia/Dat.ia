import { useReducer, useEffect } from 'react';
import { UserItem } from '../../../components/admin/AdminUsersTab';

interface UsersState {
  userList: UserItem[];
  searchQuery: string;
  sessionsUser: UserItem | null;
  resetPasswordUser: UserItem | null;
  editUser: UserItem | null;
  isNewUserModalOpen: boolean;
  isSuccessBanner: string | null;
}

type UsersAction =
  | { type: 'SET_USER_LIST'; users: UserItem[] }
  | { type: 'SET_SEARCH'; query: string }
  | { type: 'OPEN_SESSIONS'; user: UserItem }
  | { type: 'CLOSE_SESSIONS' }
  | { type: 'OPEN_RESET_PASSWORD'; user: UserItem }
  | { type: 'CLOSE_RESET_PASSWORD' }
  | { type: 'OPEN_EDIT'; user: UserItem }
  | { type: 'CLOSE_EDIT' }
  | { type: 'OPEN_NEW_USER' }
  | { type: 'CLOSE_NEW_USER' }
  | { type: 'SET_SUCCESS_BANNER'; message: string | null };

const STORAGE_KEY = 'datia_governance_users:v1';
const LEGACY_STORAGE_KEY = 'datia_governance_users';

// Cache de arranque para pintar algo mientras carga. NO es fuente de verdad:
// la respuesta de la API siempre la sobreescribe.
function loadCachedUsers(): UserItem[] | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function usersReducer(state: UsersState, action: UsersAction): UsersState {
  switch (action.type) {
    case 'SET_USER_LIST':
      return { ...state, userList: action.users };
    case 'SET_SEARCH':
      return { ...state, searchQuery: action.query };
    case 'OPEN_SESSIONS':
      return { ...state, sessionsUser: action.user };
    case 'CLOSE_SESSIONS':
      return { ...state, sessionsUser: null };
    case 'OPEN_RESET_PASSWORD':
      return { ...state, resetPasswordUser: action.user };
    case 'CLOSE_RESET_PASSWORD':
      return { ...state, resetPasswordUser: null };
    case 'OPEN_EDIT':
      return { ...state, editUser: action.user };
    case 'CLOSE_EDIT':
      return { ...state, editUser: null };
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

export function useAdminUsers(users: UserItem[], usersLoaded: boolean, onRefreshUsers?: () => void) {
  const [state, dispatch] = useReducer(
    usersReducer,
    users,
    (initial): UsersState => ({
      userList: loadCachedUsers() ?? initial,
      searchQuery: '',
      sessionsUser: null,
      resetPasswordUser: null,
      editUser: null,
      isNewUserModalOpen: false,
      isSuccessBanner: null,
    })
  );

  // La API manda. El cache solo pinta mientras la lista real no llegó. 'usersLoaded'
  // distingue "todavía cargando" de "la API devolvió []": sin eso, un entorno sin
  // usuarios dejaba la tabla mostrando los del cache y el badge un número falso.
  useEffect(() => {
    if (!usersLoaded) return;
    dispatch({ type: 'SET_USER_LIST', users });
  }, [users, usersLoaded]);

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

  const handleUserSaved = (updatedItem: UserItem) => {
    // El `updatedItem` viene del UserOut que devolvio PATCH /auth/users/{id},
    // no de los valores del formulario. Si el servidor no confirmo, el modal
    // muestra el error y esta funcion nunca corre.
    dispatch({
      type: 'SET_USER_LIST',
      users: state.userList.map((u) => (u.id === updatedItem.id ? updatedItem : u)),
    });
    dispatch({
      type: 'SET_SUCCESS_BANNER',
      message: `Perfil de '${updatedItem.name}' actualizado: ${updatedItem.role}${updatedItem.is_admin ? ' (Super Admin)' : ''}.`,
    });
    if (onRefreshUsers) onRefreshUsers();
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
    handleUserCreated,
    handleUserSaved,
  };
}
