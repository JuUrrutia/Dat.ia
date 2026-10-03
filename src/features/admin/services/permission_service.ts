import { apiClient } from '../../../shared/api/api_client';

/**
 * Fila de `GET /api/v1/permissions` (`ConnectorDomainService.list_role_table_permissions`).
 * Un dataset recien subido no aparece aca: eso es default-deny, no un fallo.
 */
export interface RoleTablePermission {
  id: number;
  connection_id: number;
  role_id: number;
  role_name: string | null;
  schema_name: string;
  table_name: string;
  is_allowed: boolean;
  granted_by_admin: boolean;
}

/**
 * Fila devuelta dentro de la respuesta de `PUT /api/v1/permissions`. OJO: el
 * router arma estos dicts a mano y NO incluye `role_id`, `connection_id` ni
 * `granted_by_admin` aunque el objeto ORM los tenga. Es lo que el servidor
 * confirmo, asi que es lo unico que esta pantalla toma como verdad.
 */
export interface ConfirmedPermission {
  id: number;
  table_name: string;
  schema_name: string;
  is_allowed: boolean;
}

/** Respuesta de `PUT /api/v1/permissions`. */
export interface SetPermissionsResponse {
  connection_id: number;
  role_id: number;
  is_allowed: boolean;
  permissions: ConfirmedPermission[];
}

export const permissionService = {
  // Sin catch: si /permissions falla (403 por rol no-admin, 500) el error sube.
  // Degradar a `[]` seria afirmar "no hay ningun permiso en la BD" cuando en
  // realidad no se pudo preguntar, y el admin veria una matriz vacia —que en
  // default-deny se lee igual que "nadie tiene acceso"— cuando no se sabe nada.
  async getPermissions(connectionId?: number): Promise<RoleTablePermission[]> {
    const params: Record<string, any> = {};
    if (connectionId) params.connection_id = connectionId;
    const res = await apiClient.get<RoleTablePermission[]>('/permissions', { params });
    return Array.isArray(res.data) ? res.data : [];
  },

  // El backend define esto con Query params, no con body: `table_names` se
  // repite una vez por tabla. Un body JSON daria 422.
  // Sin catch por la misma razon que arriba: la UI necesita el error para
  // revertir la matriz en vez de pintar casillas concedidas.
  async setPermissions(input: {
    connectionId: number;
    roleId: number;
    tableNames: string[];
    isAllowed: boolean;
  }): Promise<SetPermissionsResponse> {
    const res = await apiClient.put<SetPermissionsResponse>('/permissions', undefined, {
      params: {
        connection_id: input.connectionId,
        role_id: input.roleId,
        table_names: input.tableNames,
        is_allowed: input.isAllowed,
      },
    });
    return res.data;
  },
};