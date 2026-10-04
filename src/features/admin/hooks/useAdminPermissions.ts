import { useState, useEffect, useCallback } from 'react';
import {
  CorporateConnection,
  connectorService,
} from '../services/connector_service';
import {
  RoleTablePermission,
  ConfirmedPermission,
  GovernanceCoverage,
  permissionService,
} from '../services/permission_service';
import { authService } from '../../auth/services/auth_service';

export interface AdminRole {
  id: number;
  name: string;
  description: string;
}

/** Clave del borrador: un par (rol, tabla). */
export const permissionKey = (roleId: number, tableName: string): string => `${roleId}:${tableName}`;

/**
 * Cobertura de gobernanza de la conexion seleccionada: que tablas ve al menos un
 * rol y cuales no ve NINGUNO.
 *
 * Va aparte de `useAdminPermissions` a proposito — es un dato DERIVADO del
 * guardarrail, no de la matriz, y no tiene nada que ver con el borrador de
 * cambios: tocar una casilla no cambia la cobertura hasta que se guarda.
 */
export function useGovernanceCoverage(connectionId: number | null) {
  const [coverage, setCoverage] = useState<GovernanceCoverage | null>(null);
  const [isLoadingCoverage, setIsLoadingCoverage] = useState(false);
  const [coverageError, setCoverageError] = useState<string | null>(null);

  const fetchCoverage = useCallback(async () => {
    if (connectionId === null) {
      setCoverage(null);
      return;
    }
    setIsLoadingCoverage(true);
    setCoverageError(null);
    try {
      setCoverage(await permissionService.getCoverage(connectionId));
    } catch (err: any) {
      // No se degrada a un resumen vacio: "no se pudo calcular" y "no ve nadie
      // ninguna tabla" se verian igual en pantalla, y es exactamente el dato que
      // el admin viene a leer.
      setCoverage(null);
      setCoverageError(
        err?.response?.data?.detail ||
          'No se pudo calcular la cobertura de permisos de esta fuente.'
      );
    } finally {
      setIsLoadingCoverage(false);
    }
  }, [connectionId]);

  useEffect(() => {
    fetchCoverage();
  }, [fetchCoverage]);

  const orphanedTables = (coverage?.tables || []).filter((t) => t.coverage === 'orphaned');

  return { coverage, orphanedTables, isLoadingCoverage, coverageError, refreshCoverage: fetchCoverage };
}

export function useAdminPermissions() {
  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);

  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [rolesLoaded, setRolesLoaded] = useState(false);
  const [rolesError, setRolesError] = useState<string | null>(null);

  const [permissions, setPermissions] = useState<RoleTablePermission[]>([]);
  const [permissionsLoaded, setPermissionsLoaded] = useState(false);
  const [permissionsError, setPermissionsError] = useState<string | null>(null);
  const [isLoadingPermissions, setIsLoadingPermissions] = useState(false);

  // Borrador: lo que el admin todavia no guardo. Las casillas muestran el
  // borrador si hay, y si no lo que el servidor confirmo.
  const [draft, setDraft] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const fetchConnectors = useCallback(async () => {
    try {
      const data = await connectorService.getConnectors();
      const list = Array.isArray(data) ? data : [];
      setConnectors(list);
      setSelectedConnectionId((prev) => {
        if (prev && list.some((c) => c.id === prev)) return prev;
        const active = list.find((c) => c.is_active);
        return active ? active.id : list[0]?.id ?? null;
      });
    } catch (err: any) {
      setPermissionsError(
        err?.response?.data?.detail || 'No se pudo cargar la lista de fuentes de datos del servidor.'
      );
    }
  }, []);

  // El catalogo de roles sale de `/auth/roles`. Una constante hardcodeada
  // (CORPORATE_ROLES) tiene nombres que la base no tiene, y el PUT exigiria un
  // role_id que no existe: 404 "Rol no encontrado".
  const fetchRoles = useCallback(async () => {
    setRolesError(null);
    try {
      const data = await authService.getAvailableRoles();
      setRoles(Array.isArray(data) ? data : []);
    } catch (err: any) {
      // Sin roles no hay matriz honesta: se dice, no se inventan columnas.
      setRoles([]);
      setRolesError(
        err?.response?.data?.detail || 'No se pudo cargar el catálogo de roles del servidor.'
      );
    } finally {
      setRolesLoaded(true);
    }
  }, []);

  const fetchPermissions = useCallback(async (connectionId: number) => {
    setIsLoadingPermissions(true);
    setPermissionsError(null);
    try {
      const rows = await permissionService.getPermissions(connectionId);
      setPermissions(rows);
    } catch (err: any) {
      // No se pisa la matriz con un []: "no se pudo leer" y "no hay permisos"
      // son estados distintos y en default-deny se ven igual en pantalla.
      setPermissions([]);
      setPermissionsError(
        err?.response?.data?.detail ||
          'No se pudo leer la matriz de permisos del servidor. No se puede afirmar qué acceso existe.'
      );
    } finally {
      setIsLoadingPermissions(false);
      setPermissionsLoaded(true);
    }
  }, []);

  useEffect(() => {
    fetchConnectors();
    fetchRoles();
  }, [fetchConnectors, fetchRoles]);

  useEffect(() => {
    if (selectedConnectionId === null) return;
    setDraft({});
    setSaveError(null);
    setSaveSuccessMsg(null);
    fetchPermissions(selectedConnectionId);
  }, [selectedConnectionId, fetchPermissions]);

  const selectedConnector =
    connectors.find((c) => c.id === selectedConnectionId) || null;

  // Las tablas de la matriz son las que el servidor detecto al subir el dataset,
  // mas las que ya tienen alguna fila de permiso: si se omitiesen las ultimas,
  // revocar un permiso ya concedido seria imposible desde la pantalla.
  const tables: string[] = (() => {
    const detected = selectedConnector?.detected_tables || [];
    const granted = permissions.map((p) => p.table_name);
    return Array.from(new Set([...detected, ...granted])).sort();
  })();

  const serverAllowed = useCallback(
    (roleId: number, tableName: string): boolean =>
      permissions.some(
        (p) => p.role_id === roleId && p.table_name === tableName && p.is_allowed
      ),
    [permissions]
  );

  const grantedByAdmin = useCallback(
    (roleId: number, tableName: string): boolean =>
      permissions.some(
        (p) =>
          p.role_id === roleId && p.table_name === tableName && p.granted_by_admin
      ),
    [permissions]
  );

  const isChecked = useCallback(
    (roleId: number, tableName: string): boolean => {
      const key = permissionKey(roleId, tableName);
      return key in draft ? draft[key] : serverAllowed(roleId, tableName);
    },
    [draft, serverAllowed]
  );

  const toggleCell = (roleId: number, tableName: string) => {
    const key = permissionKey(roleId, tableName);
    setSaveError(null);
    setSaveSuccessMsg(null);
    setDraft((prev) => ({ ...prev, [key]: !isChecked(roleId, tableName) }));
  };

  /** Bulk grant: el caso normal es "este rol ve estas tablas", no 40 clics. */
  const grantAllToRole = (roleId: number) => {
    setSaveError(null);
    setSaveSuccessMsg(null);
    setDraft((prev) => {
      const next = { ...prev };
      for (const t of tables) next[permissionKey(roleId, t)] = true;
      return next;
    });
  };

  const revokeAllFromRole = (roleId: number) => {
    setSaveError(null);
    setSaveSuccessMsg(null);
    setDraft((prev) => {
      const next = { ...prev };
      for (const t of tables) next[permissionKey(roleId, t)] = false;
      return next;
    });
  };

  const pendingChanges = Object.entries(draft).filter(
    ([key, wanted]) => serverAllowed(Number(key.split(':')[0]), key.slice(key.indexOf(':') + 1)) !== wanted
  );

  const applyConfirmed = (
    prev: RoleTablePermission[],
    connectionId: number,
    roleId: number,
    confirmed: ConfirmedPermission[]
  ): RoleTablePermission[] => {
    // Solo lo que el servidor confirmo se pinta. El resto de la fila conserva
    // lo que ya se sabia del GET.
    let next = prev;
    for (const c of confirmed) {
      const idx = next.findIndex(
        (p) => p.connection_id === connectionId && p.role_id === roleId && p.table_name === c.table_name
      );
      if (idx === -1) {
        next = [
          ...next,
          {
            id: c.id,
            connection_id: connectionId,
            role_id: roleId,
            role_name: roles.find((r) => r.id === roleId)?.name ?? null,
            schema_name: c.schema_name,
            table_name: c.table_name,
            is_allowed: c.is_allowed,
            granted_by_admin: true,
          },
        ];
      } else {
        const row = next[idx];
        next = [
          ...next.slice(0, idx),
          { ...row, is_allowed: c.is_allowed, granted_by_admin: true },
          ...next.slice(idx + 1),
        ];
      }
    }
    return next;
  };

  const savePending = async (): Promise<void> => {
    if (selectedConnectionId === null || pendingChanges.length === 0) return;
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccessMsg(null);

    // Se agrupa por (rol, decision) porque el endpoint recibe un conjunto de
    // tablas con un unico is_allowed.
    const groups = new Map<string, { roleId: number; tableNames: string[]; isAllowed: boolean }>();
    for (const [key, wanted] of pendingChanges) {
      const sep = key.indexOf(':');
      const roleId = Number(key.slice(0, sep));
      const tableName = key.slice(sep + 1);
      const gk = `${roleId}:${wanted}`;
      const g = groups.get(gk) || { roleId, tableNames: [], isAllowed: wanted };
      g.tableNames.push(tableName);
      groups.set(gk, g);
    }

    let confirmedCount = 0;
    try {
      for (const g of groups.values()) {
        const res = await permissionService.setPermissions({
          connectionId: selectedConnectionId,
          roleId: g.roleId,
          tableNames: g.tableNames,
          isAllowed: g.isAllowed,
        });
        setPermissions((prev) =>
          applyConfirmed(prev, selectedConnectionId, g.roleId, res.permissions || [])
        );
        confirmedCount += (res.permissions || []).length;
      }
      // Solo se vacia el borrador si TODOS los PUT respondieron. Un fallo a
      // medias deja el borrador vivo para reintentar lo que falto.
      setDraft((prev) => {
        const rest = { ...prev };
        for (const [key] of pendingChanges) delete rest[key];
        return rest;
      });
      setSaveSuccessMsg(
        `Servidor confirmó ${confirmedCount} ${confirmedCount === 1 ? 'permiso' : 'permisos'} aplicado(s).`
      );
    } catch (err: any) {
      // REVERSION: el borrador se descarta entero y las casillas vuelven a lo que
      // el servidor tiene. Dejar el borrador puesto seria mostrar el acceso como
      // concedido cuando el PUT no lo confirmo.
      setDraft({});
      setSaveError(
        err?.response?.data?.detail ||
          'El servidor no confirmó la concesión. Ningún permiso fue aplicado y la matriz volvió a su estado anterior.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return {
    connectors,
    selectedConnectionId,
    selectedConnector,
    handleSelectConnection: setSelectedConnectionId,
    isLoadingPermissions,
    permissionsLoaded,
    permissionsError,
    roles,
    rolesLoaded,
    rolesError,
    tables,
    isChecked,
    grantedByAdmin,
    toggleCell,
    grantAllToRole,
    revokeAllFromRole,
    pendingCount: pendingChanges.length,
    savePending,
    isSaving,
    saveError,
    saveSuccessMsg,
    refresh: () => {
      if (selectedConnectionId !== null) fetchPermissions(selectedConnectionId);
    },
  };
}