import { useState, useEffect, useCallback, useRef } from 'react';
import {
  CatalogItem,
  DataDictionaryResponse,
  catalogService,
} from '../../../services/catalog_service';
import {
  CorporateConnection,
  connectorService,
} from '../../../services/connector_service';

export function useAdminCatalog() {
  const [subTab, setSubTab] = useState<'catalog' | 'dictionary'>('catalog');

  // Corporate Connections State
  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [isLoadingConnectors, setIsLoadingConnectors] = useState(false);

  // Semantic Catalog State
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(false);
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // AI Auto-enrichment State
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichSuccessMsg, setEnrichSuccessMsg] = useState<string | null>(null);
  const [enrichErrorMsg, setEnrichErrorMsg] = useState<string | null>(null);

  // Technical Data Dictionary State
  const [dataDictionary, setDataDictionary] = useState<DataDictionaryResponse | null>(null);
  const [isLoadingDictionary, setIsLoadingDictionary] = useState(false);
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({});

  const selectedConnRef = useRef<number | null>(null);
  selectedConnRef.current = selectedConnectionId;

  // 1. Fetch available connections
  const fetchConnectors = useCallback(async () => {
    setIsLoadingConnectors(true);
    try {
      const data = await connectorService.getConnectors();
      setConnectors(data || []);
      if (data && data.length > 0) {
        setSelectedConnectionId((prev) => {
          if (prev && data.some((c) => c.id === prev)) {
            return prev;
          }
          const active = data.find((c) => c.is_active);
          return active ? active.id : data[0].id;
        });
      }
    } catch {
      // Fallback
    } finally {
      setIsLoadingConnectors(false);
    }
  }, []);

  // 2. Fetch Catalog for active/selected connection
  const fetchCatalogData = useCallback(async (connId?: number | null) => {
    const targetId = connId !== undefined ? connId : selectedConnRef.current;
    setIsLoadingCatalog(true);
    try {
      const data = await catalogService.getCatalog(targetId || undefined);
      setItems(data);
    } catch {
      // Fallback
    } finally {
      setIsLoadingCatalog(false);
    }
  }, []);

  // 3. Fetch Dictionary for active/selected connection
  const fetchDictionaryData = useCallback(async (connId?: number | null) => {
    const targetId = connId !== undefined ? connId : selectedConnRef.current;
    setIsLoadingDictionary(true);
    try {
      const data = await catalogService.getDataDictionary(targetId || undefined);
      setDataDictionary(data);
      // Auto-expand first 3 tables
      const initialExpanded: Record<string, boolean> = {};
      data.tables.forEach((t, idx) => {
        initialExpanded[t.table_name] = idx < 3;
      });
      setExpandedTables(initialExpanded);
    } catch {
      // Fallback
    } finally {
      setIsLoadingDictionary(false);
    }
  }, []);

  // Initial load: Fetch connectors first
  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  // When selectedConnectionId changes, re-fetch catalog and dictionary
  useEffect(() => {
    if (selectedConnectionId !== null) {
      fetchCatalogData(selectedConnectionId);
      fetchDictionaryData(selectedConnectionId);
    }
  }, [selectedConnectionId, fetchCatalogData, fetchDictionaryData]);

  const handleSelectConnection = (connId: number) => {
    setSelectedConnectionId(connId);
  };

  const handleRunAiAutoEnrich = async () => {
    setIsEnriching(true);
    setEnrichSuccessMsg(null);
    setEnrichErrorMsg(null);
    try {
      const res = await catalogService.autoEnrich(selectedConnectionId || undefined);
      setEnrichSuccessMsg(res.message);
      await fetchCatalogData(selectedConnectionId);
      await fetchDictionaryData(selectedConnectionId);
      setTimeout(() => setEnrichSuccessMsg(null), 5000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Error al auto-enriquecer el catálogo.';
      setEnrichErrorMsg(msg);
      setTimeout(() => setEnrichErrorMsg(null), 6000);
    } finally {
      setIsEnriching(false);
    }
  };

  const handleSaveEdit = async (desc: string, formula: string) => {
    if (!editingItem) return;
    try {
      await catalogService.updateCatalogItem(editingItem.id, {
        description: desc,
        business_formula: formula,
      });
      await fetchCatalogData(selectedConnectionId);
      await fetchDictionaryData(selectedConnectionId);
    } catch {
      setItems((prev) =>
        prev.map((i) => (i.id === editingItem.id ? { ...i, description: desc, business_formula: formula } : i))
      );
    }
    setEditingItem(null);
  };

  const handleAddItem = async (newItem: {
    table: string;
    column: string;
    desc: string;
    formula: string;
    is_ai: boolean;
    connection_id?: number;
  }) => {
    try {
      await catalogService.createCatalogItem({
        connection_id: newItem.connection_id || selectedConnectionId || 1,
        table_name: newItem.table,
        column_name: newItem.column,
        description: newItem.desc,
        business_formula: newItem.formula,
        is_ai_generated: newItem.is_ai,
      });
      await fetchCatalogData(selectedConnectionId);
      await fetchDictionaryData(selectedConnectionId);
    } catch {
      // Fallback
    }
    setIsAddModalOpen(false);
  };

  const handleDeleteItem = async (id: number, table: string, column?: string) => {
    const label = column ? `${table}.${column}` : table;
    if (!window.confirm(`¿Estás seguro de eliminar la regla del catálogo para '${label}'?`)) return;
    try {
      await catalogService.deleteCatalogItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      await fetchDictionaryData(selectedConnectionId);
    } catch {
      // Fallback
    }
  };

  const toggleTableExpansion = (tableName: string) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  const selectedConnector = connectors.find((c) => c.id === selectedConnectionId) || null;

  return {
    subTab,
    setSubTab,
    connectors,
    selectedConnectionId,
    selectedConnector,
    isLoadingConnectors,
    handleSelectConnection,
    items,
    isLoadingCatalog,
    editingItem,
    setEditingItem,
    isAddModalOpen,
    setIsAddModalOpen,
    isEnriching,
    enrichSuccessMsg,
    enrichErrorMsg,
    dataDictionary,
    isLoadingDictionary,
    expandedTables,
    handleRunAiAutoEnrich,
    handleSaveEdit,
    handleAddItem,
    handleDeleteItem,
    toggleTableExpansion,
    refreshAll: () => {
      fetchConnectors();
      fetchCatalogData(selectedConnectionId);
      fetchDictionaryData(selectedConnectionId);
    },
  };
}
