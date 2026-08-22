import { apiClient } from './api_client';

export interface CatalogItem {
  id: number;
  connection_id: number;
  domain_id?: number;
  schema_name: string;
  table_name: string;
  column_name?: string;
  friendly_name?: string;
  description: string;
  synonyms?: string;
  business_formula?: string;
  is_ai_generated: boolean;
  updated_at?: string;
}

export interface DataDictionaryColumn {
  name: string;
  data_type: string;
  is_pk: boolean;
  is_nullable: boolean;
  default_value?: string | null;
  sample_values: string[];
  friendly_name?: string | null;
  description?: string | null;
  business_formula?: string | null;
  is_ai_generated: boolean;
}

export interface DataDictionaryTable {
  table_name: string;
  schema_name: string;
  row_count: number;
  column_count: number;
  description?: string | null;
  columns: DataDictionaryColumn[];
}

export interface DataDictionaryResponse {
  connection_id: number;
  connection_name: string;
  db_type: string;
  tables: DataDictionaryTable[];
  total_tables: number;
  total_columns: number;
}

export interface AutoEnrichResponse {
  success: boolean;
  message: string;
  enriched_count: number;
  catalog_items: CatalogItem[];
}

export const catalogService = {
  async getCatalog(connectionId?: number, tableName?: string): Promise<CatalogItem[]> {
    try {
      const params: Record<string, any> = {};
      if (connectionId) params.connection_id = connectionId;
      if (tableName) params.table_name = tableName;
      const res = await apiClient.get<CatalogItem[]>('/catalog', { params });
      return res.data;
    } catch {
      return [];
    }
  },

  async createCatalogItem(item: {
    connection_id?: number;
    schema_name?: string;
    table_name: string;
    column_name?: string;
    friendly_name?: string;
    description: string;
    synonyms?: string;
    business_formula?: string;
    is_ai_generated?: boolean;
  }): Promise<CatalogItem> {
    const res = await apiClient.post<CatalogItem>('/catalog', {
      connection_id: item.connection_id || 1,
      schema_name: item.schema_name || 'main',
      table_name: item.table_name,
      column_name: item.column_name || null,
      friendly_name: item.friendly_name || null,
      description: item.description,
      synonyms: item.synonyms || null,
      business_formula: item.business_formula || 'Columna directa',
      is_ai_generated: item.is_ai_generated ?? false,
    });
    return res.data;
  },

  async updateCatalogItem(
    id: number,
    item: {
      friendly_name?: string;
      description?: string;
      synonyms?: string;
      business_formula?: string;
      is_ai_generated?: boolean;
    }
  ): Promise<CatalogItem> {
    const res = await apiClient.put<CatalogItem>(`/catalog/${id}`, item);
    return res.data;
  },

  async deleteCatalogItem(id: number): Promise<void> {
    await apiClient.delete(`/catalog/${id}`);
  },

  async getDataDictionary(connectionId?: number): Promise<DataDictionaryResponse> {
    try {
      const params: Record<string, any> = {};
      if (connectionId) params.connection_id = connectionId;
      const res = await apiClient.get<DataDictionaryResponse>('/catalog/data-dictionary', { params });
      return res.data;
    } catch {
      return {
        connection_id: connectionId || 1,
        connection_name: 'Base de Datos',
        db_type: 'sqlite',
        tables: [],
        total_tables: 0,
        total_columns: 0,
      };
    }
  },

  async autoEnrich(connectionId?: number, tableName?: string): Promise<AutoEnrichResponse> {
    const res = await apiClient.post<AutoEnrichResponse>('/catalog/auto-enrich', {
      connection_id: connectionId || null,
      table_name: tableName || null,
    });
    return res.data;
  },
};
