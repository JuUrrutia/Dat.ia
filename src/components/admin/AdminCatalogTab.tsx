import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, Check, Plus, BookOpen, Database } from 'lucide-react';
import {
  CatalogItem,
  DataDictionaryResponse,
  catalogService,
} from '../../services/catalog_service';
import { CatalogEditModal } from './CatalogEditModal';
import { CatalogAddModal } from './CatalogAddModal';
import { SemanticCatalogSection } from './catalog/SemanticCatalogSection';
import { DataDictionarySection } from './catalog/DataDictionarySection';

interface AdminCatalogTabProps {
  catalog?: any[];
  aiEnriching?: boolean;
  aiSuccess?: boolean;
  onRunAiCatalog?: () => void;
}

export const AdminCatalogTab: React.FC<AdminCatalogTabProps> = () => {
  const [subTab, setSubTab] = useState<'catalog' | 'dictionary'>('catalog');

  // Semantic Catalog State
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(false);
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // AI Auto-enrichment State
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichSuccessMsg, setEnrichSuccessMsg] = useState<string | null>(null);

  // Technical Data Dictionary State
  const [dataDictionary, setDataDictionary] = useState<DataDictionaryResponse | null>(null);
  const [isLoadingDictionary, setIsLoadingDictionary] = useState(false);
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({});

  const fetchCatalogData = useCallback(async () => {
    setIsLoadingCatalog(true);
    try {
      const data = await catalogService.getCatalog();
      setItems(data);
    } catch {
      // Fallback
    } finally {
      setIsLoadingCatalog(false);
    }
  }, []);

  const fetchDictionaryData = useCallback(async () => {
    setIsLoadingDictionary(true);
    try {
      const data = await catalogService.getDataDictionary();
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

  useEffect(() => {
    fetchCatalogData();
    fetchDictionaryData();
  }, [fetchCatalogData, fetchDictionaryData]);

  const handleRunAiAutoEnrich = async () => {
    setIsEnriching(true);
    setEnrichSuccessMsg(null);
    try {
      const res = await catalogService.autoEnrich();
      setEnrichSuccessMsg(res.message);
      await fetchCatalogData();
      await fetchDictionaryData();
      setTimeout(() => setEnrichSuccessMsg(null), 4500);
    } catch (err: any) {
      setEnrichSuccessMsg(err.message || 'Error al auto-enriquecer el catálogo.');
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
      await fetchCatalogData();
      await fetchDictionaryData();
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
  }) => {
    try {
      await catalogService.createCatalogItem({
        table_name: newItem.table,
        column_name: newItem.column,
        description: newItem.desc,
        business_formula: newItem.formula,
        is_ai_generated: newItem.is_ai,
      });
      await fetchCatalogData();
      await fetchDictionaryData();
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
      await fetchDictionaryData();
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

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 border border-white/10 space-y-6">
      {/* Header and Subtab Navigation */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div className="space-y-1">
          <h3 className="text-sm sm:text-base font-semibold text-white flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" />
            Gobernanza Semántica & Diccionario de Datos Dinámico
          </h3>
          <p className="text-xs text-gray-400">
            Metadatos dinámicos, tipos de datos reales y contexto de negocio para el motor Text-to-SQL con IA
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Subtab Toggle Buttons */}
          <div className="flex items-center bg-dark-base p-1 rounded-xl border border-dark-border">
            <button
              type="button"
              onClick={() => setSubTab('catalog')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                subTab === 'catalog'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Catálogo Semántico ({items.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setSubTab('dictionary')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                subTab === 'dictionary'
                  ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Diccionario de Datos ({dataDictionary?.total_tables || 0} Tablas)</span>
            </button>
          </div>

          {subTab === 'catalog' && (
            <button
              type="button"
              onClick={() => setIsAddModalOpen(true)}
              className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-gray-200 border border-dark-border px-3 py-2 rounded-xl transition-colors font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Añadir Regla</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleRunAiAutoEnrich}
            disabled={isEnriching}
            className="flex items-center space-x-2 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors disabled:opacity-50"
          >
            <Sparkles className={`w-4 h-4 ${isEnriching ? 'animate-spin' : ''}`} />
            <span>{isEnriching ? 'Auto-enriqueciendo con IA...' : 'Auto-enriquecer con IA'}</span>
          </button>
        </div>
      </div>

      {enrichSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4 shrink-0" />
          <span>{enrichSuccessMsg}</span>
        </div>
      )}

      {/* Subtab 1: Semantic Catalog */}
      {subTab === 'catalog' && (
        <SemanticCatalogSection
          items={items}
          isLoadingCatalog={isLoadingCatalog}
          onOpenEditModal={(item) => setEditingItem(item)}
          onDeleteItem={handleDeleteItem}
        />
      )}

      {/* Subtab 2: Technical Data Dictionary */}
      {subTab === 'dictionary' && (
        <DataDictionarySection
          dataDictionary={dataDictionary}
          isLoadingDictionary={isLoadingDictionary}
          expandedTables={expandedTables}
          onToggleTableExpansion={toggleTableExpansion}
        />
      )}

      {/* Edit Rule Modal */}
      <CatalogEditModal
        isOpen={Boolean(editingItem)}
        item={editingItem as any}
        onClose={() => setEditingItem(null)}
        onSave={handleSaveEdit}
      />

      {/* Add New Rule Modal */}
      <CatalogAddModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddItem as any}
      />
    </div>
  );
};
