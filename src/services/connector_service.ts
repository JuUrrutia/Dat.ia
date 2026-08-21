import { apiClient } from './api_client';

export interface CorporateConnection {
  id: number;
  name: string;
  db_type: 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite';
  host: string;
  port: number;
  database_name: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface ConnectionFormData {
  name: string;
  db_type: 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite';
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

const STORAGE_KEY = 'datia_corporate_connectors:v1';
const LEGACY_STORAGE_KEY = 'datia_corporate_connectors';

export const DEFAULT_CONNECTORS: CorporateConnection[] = [];

export const connectorService = {
  getStoredConnectors(): CorporateConnection[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length >= 0) {
          return parsed;
        }
      }
    } catch {
      // Fallback
    }
    return DEFAULT_CONNECTORS;
  },

  saveConnectorsToStorage(list: CorporateConnection[]): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch {
      // Ignore storage quota errors
    }
  },

  async getConnectors(): Promise<CorporateConnection[]> {
    const stored = this.getStoredConnectors();
    try {
      const res = await apiClient.get<CorporateConnection[]>('/connectors');
      if (res.data && res.data.length > 0) {
        // Merge API connectors with stored active states
        const merged = res.data.map((apiConn) => {
          const matchedStored = stored.find((s) => s.id === apiConn.id || s.name === apiConn.name);
          return matchedStored ? { ...apiConn, is_active: matchedStored.is_active } : apiConn;
        });
        this.saveConnectorsToStorage(merged);
        return merged;
      }
    } catch {
      // API offline or empty, use stored
    }
    return stored;
  },

  toggleActive(id: number): CorporateConnection[] {
    const current = this.getStoredConnectors();
    const updated = current.map((c) => (c.id === id ? { ...c, is_active: !c.is_active } : c));
    this.saveConnectorsToStorage(updated);
    return updated;
  },

  async createConnector(data: ConnectionFormData): Promise<CorporateConnection> {
    let newConn: CorporateConnection;
    try {
      const res = await apiClient.post<CorporateConnection>('/connectors', data);
      newConn = res.data;
    } catch {
      newConn = {
        id: Date.now(),
        name: data.name,
        db_type: data.db_type,
        host: data.host,
        port: data.port,
        database_name: data.database_name,
        username: data.username,
        is_active: data.is_active ?? true,
        created_at: new Date().toISOString().split('T')[0],
      };
    }

    const current = this.getStoredConnectors();
    const updated = [...current, newConn];
    this.saveConnectorsToStorage(updated);
    return newConn;
  },

  async updateConnector(id: number, data: Partial<ConnectionFormData>): Promise<CorporateConnection> {
    try {
      await apiClient.put<CorporateConnection>(`/connectors/${id}`, data);
    } catch {
      // Local fallback
    }

    const current = this.getStoredConnectors();
    let updatedItem: CorporateConnection | null = null;
    const updated = current.map((c) => {
      if (c.id === id) {
        updatedItem = {
          ...c,
          ...(data.name ? { name: data.name } : {}),
          ...(data.db_type ? { db_type: data.db_type } : {}),
          ...(data.host ? { host: data.host } : {}),
          ...(data.port !== undefined ? { port: data.port } : {}),
          ...(data.database_name ? { database_name: data.database_name } : {}),
          ...(data.username ? { username: data.username } : {}),
          ...(data.is_active !== undefined ? { is_active: data.is_active } : {}),
        };
        return updatedItem;
      }
      return c;
    });

    this.saveConnectorsToStorage(updated);
    return updatedItem || current[0];
  },

  async deleteConnector(id: number): Promise<void> {
    try {
      await apiClient.delete(`/connectors/${id}`);
    } catch {
      // Local fallback
    }
    const current = this.getStoredConnectors();
    const updated = current.filter((c) => c.id !== id);
    this.saveConnectorsToStorage(updated);
  },

  resetConnectors(): CorporateConnection[] {
    this.saveConnectorsToStorage(DEFAULT_CONNECTORS);
    return DEFAULT_CONNECTORS;
  },

  async testConnection(data: ConnectionFormData): Promise<ConnectionTestResult> {
    try {
      const res = await apiClient.post<ConnectionTestResult>('/connectors/test', data);
      return res.data;
    } catch (err: any) {
      return {
        success: false,
        message: err.response?.data?.detail || `No se pudo conectar a ${data.host}:${data.port} (${data.db_type.toUpperCase()}). Verifica la dirección y puerto.`,
        latency_ms: 0,
      };
    }
  },
};
