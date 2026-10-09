import { apiClient } from '../../../shared/api/api_client';

export interface CorporateConnection {
  id: number;
  name: string;
  db_type: 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite';
  host: string;
  port: number;
  database_name: string;
  username: string;
  is_active: boolean;
  is_uploaded?: boolean;
  requires_permission_review?: boolean;
  detected_tables?: string[];
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
  is_uploaded?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency_ms: number;
}

const STORAGE_KEY_PREFIX = 'datia_corporate_connectors:v1';
const USER_KEY = 'datia_auth_user:v1';

// El cache guarda host, database_name y username: es infraestructura de un
// usuario concreto. Con una clave global, el usuario B en la misma maquina
// leia los conectores de A cuando la API caia. Namespace por user.id.
function currentUserScope(): string {
  try {
    const raw = localStorage.getItem(USER_KEY);
    const id = raw ? JSON.parse(raw)?.id : null;
    return id != null ? String(id) : 'anon';
  } catch {
    return 'anon';
  }
}

function storageKey(): string {
  return `${STORAGE_KEY_PREFIX}:${currentUserScope()}`;
}

export const DEFAULT_CONNECTORS: CorporateConnection[] = [];

export const connectorService = {
  getStoredConnectors(): CorporateConnection[] {
    try {
      const stored = localStorage.getItem(storageKey());
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length >= 0) {
          return parsed;
        }
      }
    } catch {
      // Cache ilegible: se sigue con la lista vacia y la API manda.
    }
    return DEFAULT_CONNECTORS;
  },

  saveConnectorsToStorage(list: CorporateConnection[]): void {
    try {
      localStorage.setItem(storageKey(), JSON.stringify(list));
    } catch {
      // Ignore storage quota errors
    }
  },

  async getConnectors(): Promise<CorporateConnection[]> {
    try {
      const res = await apiClient.get<CorporateConnection[]>('/connectors');
      // API sana: '[]' es "no hay conectores", no un error. No caer a la cache local.
      const list = Array.isArray(res.data) ? res.data : [];
      this.saveConnectorsToStorage(list);
      return list;
    } catch {
      // API caida: se usa la cache local como ultimo recurso.
      return this.getStoredConnectors();
    }
  },

  async toggleActive(id: number): Promise<CorporateConnection[]> {
    // Sin fallback: el estado nuevo es el que devuelve el servidor. Invertirlo
    // localmente tras un fallo hacia cambiar el punto de la UI sin cambiar la BD.
    const res = await apiClient.post<CorporateConnection>(`/connectors/${id}/toggle-active`);
    const current = this.getStoredConnectors();
    const updated = current.some((c) => c.id === id)
      ? current.map((c) => (c.id === id ? res.data : c))
      : [res.data, ...current];
    this.saveConnectorsToStorage(updated);
    return updated;
  },

  async createConnector(data: ConnectionFormData): Promise<CorporateConnection> {
    try {
      const res = await apiClient.post<CorporateConnection>('/connectors', data);
      const current = this.getStoredConnectors();
      const updated = [res.data, ...current.filter((c) => c.id !== res.data.id)];
      this.saveConnectorsToStorage(updated);
      return res.data;
    } catch (err) {
      // Sin fallback: una conexion solo existe si el servidor la creo.
      throw err;
    }
  },

  async uploadDatabase(file: File, name?: string): Promise<CorporateConnection> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }
    const res = await apiClient.post<CorporateConnection>('/connectors/upload', formData);
    const current = this.getStoredConnectors();
    const updated = [res.data, ...current.filter((c) => c.id !== res.data.id)];
    this.saveConnectorsToStorage(updated);
    return res.data;
  },

  async updateConnector(id: number, data: Partial<ConnectionFormData>): Promise<CorporateConnection> {
    // Sin fallback: una conexion solo existe, y solo cambia, si el servidor la
    // confirmo. Antes el catch armaba un objeto local y lo devolvia como si fuera
    // la respuesta, asi que useConnectorForm cerraba el modal como "guardado" y
    // un reload revertia todo.
    const res = await apiClient.put<CorporateConnection>(`/connectors/${id}`, data);
    const current = this.getStoredConnectors();
    const updated = current.map((c) => (c.id === id ? res.data : c));
    this.saveConnectorsToStorage(updated);
    return res.data;
  },

  async deleteConnector(id: number): Promise<void> {
    // Sin fallback: si el DELETE falla la conexion sigue viva en el servidor y
    // la tarjeta no puede desaparecer de la UI.
    await apiClient.delete(`/connectors/${id}`);
    const current = this.getStoredConnectors();
    this.saveConnectorsToStorage(current.filter((c) => c.id !== id));
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
