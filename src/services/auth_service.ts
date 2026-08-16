import { apiClient } from './api_client';
import { User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const res = await apiClient.post<LoginResponse>('/auth/login', { username, password });
    if (res.data.access_token) {
      localStorage.setItem('token', res.data.access_token);
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
        { id: 1, name: 'Analista de Finanzas y Ventas', description: 'Acceso a finanzas y ventas' },
        { id: 2, name: 'Ejecutivo Comercial', description: 'Acceso a ventas y clientes' },
      ];
    }
  },

  logout() {
    localStorage.removeItem('token');
  }
};

