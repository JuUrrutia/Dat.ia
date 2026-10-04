import { useState, useEffect, useCallback } from 'react';
import { connectorService } from '../services/connector_service';
import { CorporateConnection } from '../services/connector_service';
import { GoldenQuery, learningMemoryService } from '../services/learning_memory_service';

/**
 * Estado de la pestana "Aprendizaje": que aprendio el motor de esta conexion y
 * como se deshace.
 *
 * Un solo hook para lo minimo que la pantalla necesita: conectores (el selector
 * ya existe en `useAdminPermissions`, pero arrastrarlo aca solo para llamarlo dos
 * veces seria duplicar estado), listado y borrado.
 */
export function useAdminLearned() {
  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);

  const [items, setItems] = useState<GoldenQuery[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    connectorService
      .getConnectors()
      .then((list) => {
        const rows = Array.isArray(list) ? list : [];
        setConnectors(rows);
        setSelectedConnectionId((prev) => {
          if (prev && rows.some((c) => c.id === prev)) return prev;
          const active = rows.find((c) => c.is_active);
          return active ? active.id : rows[0]?.id ?? null;
        });
      })
      .catch((err: any) =>
        setError(
          err?.response?.data?.detail ||
            'No se pudo cargar la lista de fuentes de datos del servidor.'
        )
      );
  }, []);

  const fetchItems = useCallback(async (connectionId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await learningMemoryService.listGoldenQueries(connectionId);
      setItems(data.items);
    } catch (err: any) {
      // No se pisa la lista con []: "no se pudo leer" y "no hay nada aprendido"
      // son afirmaciones distintas y esta pantalla es de control.
      setItems([]);
      setError(
        err?.response?.data?.detail ||
          'No se pudo leer la memoria de aprendizaje del servidor. No se puede afirmar qué se está inyectando en el prompt.'
      );
    } finally {
      setIsLoading(false);
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (selectedConnectionId === null) return;
    setActionError(null);
    fetchItems(selectedConnectionId);
  }, [selectedConnectionId, fetchItems]);

  /** Borra de verdad contra el servidor y recien entonces saca la fila de la lista. */
  const deleteItem = useCallback(
    async (id: number) => {
      setDeletingId(id);
      setActionError(null);
      try {
        await learningMemoryService.deleteGoldenQuery(id);
        setItems((prev) => prev.filter((i) => i.id !== id));
        return true;
      } catch (err: any) {
        setActionError(
          err?.response?.data?.detail ||
            'El servidor no confirmó el borrado. La memoria sigue inyectándose en el prompt.'
        );
        return false;
      } finally {
        setDeletingId(null);
      }
    },
    []
  );

  return {
    connectors,
    selectedConnectionId,
    selectedConnector: connectors.find((c) => c.id === selectedConnectionId) || null,
    handleSelectConnection: setSelectedConnectionId,
    items,
    isLoading,
    loaded,
    error,
    actionError,
    deletingId,
    deleteItem,
    refresh: () => {
      if (selectedConnectionId !== null) fetchItems(selectedConnectionId);
    },
  };
}