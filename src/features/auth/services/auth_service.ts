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

  async getAvailableRoles(): Promise<{ id: number; name: string; description: string }[]> {
    try {
      const res = await apiClient.get('/auth/roles');
      return res.data;
    } catch {
      return [
        { id: 1, name: 'Economista', description: 'Acceso a información económica, financiera, facturación y costos' },
        { id: 2, name: 'TI', description: 'Acceso a métricas de infraestructura, rendimiento de servidores e incidentes' },
        { id: 3, name: 'Usuario', description: 'Perfil inicial por defecto sin asignación de dominios' },
      ];
    }
  },

  async getUsers(): Promise<User[]> {
    try {
      const res = await apiClient.get<User[]>('/auth/users');
      return res.data;
    } catch {
      return [
        { id: 1, username: 'admin', email: 'admin@empresa.com', role_name: 'Administrador', is_admin: true },
        { id: 2, username: 'economista', email: 'economista@empresa.com', role_name: 'Economista', is_admin: false },
        { id: 3, username: 'ti', email: 'ti@empresa.com', role_name: 'TI', is_admin: false }
      ];
    }
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
