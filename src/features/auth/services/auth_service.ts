import { apiClient, setAuthToken } from '../../../shared/api/api_client';
import { User, UserSession, PasswordResetResult } from '../../../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>('/auth/login', { username, password });
    if (res.data.access_token) {
      setAuthToken(res.data.access_token);
    }
    return res.data;
  },

  async register(data: {
    username: string;
    email?: string;
    password: string;
    role_id?: number;
    is_admin?: boolean;
  }): Promise<User> {
    const res = await apiClient.post<User>('/auth/register', data);
    return res.data;
  },

  async getCurrentUser(): Promise<User> {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  // Sin fallback: si /auth/roles falla (ej. 403 por rol no-admin), el error sube.
  // Devolver roles ficticios hacía creer al usuario que tenía permisos que no tiene.
  async getAvailableRoles(): Promise<{ id: number; name: string; description: string }[]> {
    const res = await apiClient.get<{ id: number; name: string; description: string }[]>('/auth/roles');
    return res.data;
  },

  // Sin fallback: /auth/users exige rol admin. Un 403 debe llegar visible al
  // consumidor, no disfrazarse de "hay 3 usuarios y uno es Super Admin".
  async getUsers(): Promise<User[]> {
    const res = await apiClient.get<User[]>('/auth/users');
    return res.data;
  },

  // Sin catch: si el servidor no confirma, el error sube. Un "Guardar Rol" que
  // escribe en localStorage y anuncia exito es exactamente el bug que se
  // elimino de la UI; con este metodo la UI tiene algo real que esperar.
  async updateUserRole(userId: number, data: { role?: string; is_admin?: boolean }): Promise<User> {
    const res = await apiClient.patch<User>(`/auth/users/${userId}`, data);
    return res.data;
  },

  async getUserSessions(userId?: number): Promise<UserSession[]> {
    const params = userId ? { user_id: userId } : {};
    const res = await apiClient.get<UserSession[]>('/auth/sessions', { params });
    return res.data;
  },

  async revokeSession(sessionId: number): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>(`/auth/sessions/${sessionId}/revoke`);
    return res.data;
  },

  async revokeAllUserSessions(userId: number): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>(`/auth/users/${userId}/revoke-all-sessions`);
    return res.data;
  },

  async resetUserPassword(userId: number): Promise<PasswordResetResult> {
    const res = await apiClient.post<PasswordResetResult>(`/auth/users/${userId}/reset-password`);
    return res.data;
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
    const res = await apiClient.post<{ message: string }>('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    });
    return res.data;
  },

  logout() {
    setAuthToken(null);
  }
};
