import { apiClient, setAuthToken } from './api_client';
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

  logout() {
    setAuthToken(null);
  }
};
