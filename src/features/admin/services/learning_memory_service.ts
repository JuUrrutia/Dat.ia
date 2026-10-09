import { apiClient } from '../../../shared/api/api_client';

/**
 * Fila de `GET /chat/golden-queries`.
 *
 * `user_role` NO es el autor: `query_learning_memories` no tiene `user_id`, asi
 * que la API no puede decir quien escribio el SQL y esta pantalla no lo insinua.
 * `execution_count` es el uso real medido (veces inyectada en el prompt de la
 * conexion) y es el dato que hace util la pantalla.
 */
export interface GoldenQuery {
  id: number;
  question_pattern: string;
  successful_sql: string;
  user_role: string | null;
  is_golden: boolean;
  execution_count: number;
  was_self_healed: boolean;
  created_at: string;
  updated_at: string;
}

export interface GoldenQueryList {
  items: GoldenQuery[];
  total: number;
}

export const learningMemoryService = {
  // Sin catch, igual que `permissionService`: "no se pudo leer" y "no hay nada"
  // son estados distintos y en pantalla se ven igual. Degradar a [] seria
  // afirmar que la memoria esta vacia cuando en realidad no se pudo preguntar.
  async listGoldenQueries(connectionId: number): Promise<GoldenQueryList> {
    const res = await apiClient.get<GoldenQueryList>('/chat/golden-queries', {
      params: { connection_id: connectionId },
    });
    return {
      items: Array.isArray(res.data?.items) ? res.data.items : [],
      total: typeof res.data?.total === 'number' ? res.data.total : 0,
    };
  },

  /** 404 si la memoria no existe: un borrado fallido tiene que decirse. */
  async deleteGoldenQuery(memoryId: number): Promise<{ success: boolean; message: string }> {
    const res = await apiClient.delete<{ success: boolean; message: string }>(
      `/chat/golden-queries/${memoryId}`
    );
    return res.data;
  },
};