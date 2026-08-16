import { apiClient } from './api_client';

export interface CorporateConnection {
  id: number;
  name: string;
  db_type: 'postgresql' | 'mssql' | 'mysql' | 'oracle';
  host: string;
  port: number;
  database_name: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface ConnectionFormData {
  name: string;
  db_type: 'postgresql' | 'mssql' | 'mysql' | 'oracle';
  host: string;
  port: number;
  database_name: string;
  username: string;
  password?: string;
  is_active?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency_ms: number;
}

export const connectorService = {
  async getConnectors(): Promise<CorporateConnection[]> {
    try {
      const res = await apiClient.get<CorporateConnection[]>('/connectors');
      return res.data;
    } catch {
      // Mock connectors fallback if backend is offline
      return [
        { id: 1, name: 'BD_FINANZAS_PROD', db_type: 'postgresql', host: '10.0.1.45', port: 5432, database_name: 'corp_finanzas', username: 'usr_read_finanzas', is_active: true, created_at: '2026-08-15' },
        { id: 2, name: 'BD_VENTAS_MSSQL', db_type: 'mssql', host: '10.0.1.46', port: 1433, database_name: 'sales_warehouse', username: 'usr_read_ventas', is_active: true, created_at: '2026-08-15' },
      ];
    }
  },

  async createConnector(data: ConnectionFormData): Promise<CorporateConnection> {
    const res = await apiClient.post<CorporateConnection>('/connectors', data);
    return res.data;
  },

  async updateConnector(id: number, data: Partial<ConnectionFormData>): Promise<CorporateConnection> {
    const res = await apiClient.put<CorporateConnection>(`/connectors/${id}`, data);
    return res.data;
  },

  async deleteConnector(id: number): Promise<void> {
    await apiClient.delete(`/connectors/${id}`);
  },

  async testConnection(data: ConnectionFormData): Promise<ConnectionTestResult> {
    try {
      const res = await apiClient.post<ConnectionTestResult>('/connectors/test', data);
      return res.data;
    } catch (err: any) {
      return {
        success: false,
        message: err.response?.data?.detail || `No se pudo conectar a ${data.host}:${data.port} (${data.db_type.toUpperCase()}). Verifica la dirección y puerto.`,
        latency_ms: 0
      };
    }
  }
};
