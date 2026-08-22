import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Check,
  Search,
  Plus,
  Edit3,
  Trash2,
  BookOpen,
  Database,
  Table as TableIcon,
  Layers,
  Key,
  HelpCircle,
  RefreshCw,
  Eye,
  FileCode,
} from 'lucide-react';
import {
  CatalogItem,
  DataDictionaryResponse,
  DataDictionaryTable,
  catalogService,
} from '../../services/catalog_service';
import { CatalogEditModal } from './CatalogEditModal';
import { CatalogAddModal } from './CatalogAddModal';

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
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTableFilter, setSelectedTableFilter] = useState('ALL');
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // AI Auto-enrichment State
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichSuccessMsg, setEnrichSuccessMsg] = useState<string | null>(null);

  // Technical Data Dictionary State
  const [dataDictionary, setDataDictionary] = useState<DataDictionaryResponse | null>(null);
  const [isLoadingDictionary, setIsLoadingDictionary] = useState(false);
  const [dictSearchQuery, setDictSearchQuery] = useState('');
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
      // Local fallback
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

  // Filter Catalog Items
  const uniqueTables = Array.from(new Set(items.map((i) => i.table_name)));
  const filteredCatalogItems = items.filter((cat) => {
    const matchesSearch =
      cat.table_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (cat.column_name && cat.column_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (cat.description && cat.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (cat.friendly_name && cat.friendly_name.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesTable = selectedTableFilter === 'ALL' || cat.table_name === selectedTableFilter;
    return matchesSearch && matchesTable;
  });

  // Filter Dictionary Tables
  const filteredDictTables = (dataDictionary?.tables || []).filter((tbl) => {
    if (!dictSearchQuery.trim()) return true;
    const q = dictSearchQuery.toLowerCase();
    const matchesTableName = tbl.table_name.toLowerCase().includes(q);
    const matchesColumn = tbl.columns.some(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.data_type.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q))
    );
    return matchesTableName || matchesColumn;
  });

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

      {/* ========================================================================= */}
      {/* SUBTAB 1: SEMANTIC CATALOG (Contexto y Reglas IA) */}
      {/* ========================================================================= */}
      {subTab === 'catalog' && (
        <div className="space-y-4 animate-fadeIn">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar tabla, campo o descripción..."
                aria-label="Buscar en catálogo"
                className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>

            <div className="flex items-center space-x-2 text-xs w-full sm:w-auto">
              <label htmlFor="catalog-filter-tbl" className="text-gray-400 font-medium whitespace-nowrap">
                Filtrar por tabla:
              </label>
              <select
                id="catalog-filter-tbl"
                aria-label="Filtrar por tabla"
                value={selectedTableFilter}
                onChange={(e) => setSelectedTableFilter(e.target.value)}
                className="bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 text-xs"
              >
                <option value="ALL">Todas las Tablas ({items.length} reglas)</option>
                {uniqueTables.map((tbl) => (
                  <option key={tbl} value={tbl}>
                    {tbl}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Catalog Table */}
          <div className="overflow-x-auto rounded-xl border border-dark-border">
            <table className="w-full text-left text-xs min-w-[700px]">
              <thead className="bg-dark-base border-b border-dark-border text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Tabla BD</th>
                  <th className="px-4 py-3">Campo / Columna</th>
                  <th className="px-4 py-3">Descripción Semántica (Contexto IA)</th>
                  <th className="px-4 py-3">Fórmula / Regla</th>
                  <th className="px-4 py-3">Origen</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border text-gray-200">
                {isLoadingCatalog ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-purple-400" />
                      Cargando catálogo semántico...
                    </td>
                  </tr>
                ) : filteredCatalogItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No se encontraron entradas en el catálogo. Haz clic en "Auto-enriquecer con IA" para generarlas automáticamente.
                    </td>
                  </tr>
                ) : (
                  filteredCatalogItems.map((cat) => (
                    <tr key={cat.id} className="hover:bg-dark-card/50 transition-colors">
                      <td className="px-4 py-3 font-mono font-semibold text-purple-400">{cat.table_name}</td>
                      <td className="px-4 py-3 font-mono font-medium text-white">{cat.column_name || '(Toda la tabla)'}</td>
                      <td className="px-4 py-3 text-gray-300 max-w-md">
                        {cat.friendly_name && (
                          <span className="font-semibold text-white block mb-0.5">{cat.friendly_name}</span>
                        )}
                        <span>{cat.description}</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-gray-400 text-[11px]">{cat.business_formula || 'Directa'}</td>
                      <td className="px-4 py-3">
                        {cat.is_ai_generated ? (
                          <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded text-[10px] font-semibold">
                            IA Auto-generado
                          </span>
                        ) : (
                          <span className="bg-gray-500/10 text-gray-400 border border-gray-500/20 px-2 py-0.5 rounded text-[10px]">
                            Manual Admin
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            type="button"
                            onClick={() =>
                              setEditingItem({
                                ...cat,
                                table: cat.table_name,
                                column: cat.column_name || '',
                                desc: cat.description,
                                formula: cat.business_formula || '',
                                is_ai: cat.is_ai_generated,
                              } as any)
                            }
                            aria-label={`Editar regla para ${cat.table_name}.${cat.column_name}`}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 transition-colors"
                            title="Editar Regla"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDeleteItem(cat.id, cat.table_name, cat.column_name)}
                            aria-label={`Eliminar regla ${cat.table_name}.${cat.column_name}`}
                            className="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Eliminar Regla"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SUBTAB 2: TECHNICAL DATA DICTIONARY (Esquema Real Introspeccionado) */}
      {/* ========================================================================= */}
      {subTab === 'dictionary' && (
        <div className="space-y-4 animate-fadeIn">
          {/* Search bar and metadata overview */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={dictSearchQuery}
                onChange={(e) => setDictSearchQuery(e.target.value)}
                placeholder="Buscar tabla, columna o tipo de dato..."
                aria-label="Buscar en diccionario de datos"
                className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>

            <div className="flex items-center space-x-3 text-xs text-gray-400">
              <span className="bg-dark-base px-3 py-1.5 rounded-xl border border-dark-border">
                Base: <strong className="text-white">{dataDictionary?.connection_name || 'BD Activa'}</strong>
              </span>
              <span className="bg-dark-base px-3 py-1.5 rounded-xl border border-dark-border">
                Total: <strong className="text-purple-400">{dataDictionary?.total_tables || 0} Tablas</strong> •{' '}
                <strong className="text-cyan-400">{dataDictionary?.total_columns || 0} Columnas</strong>
              </span>
            </div>
          </div>

          {isLoadingDictionary ? (
            <div className="py-12 text-center text-gray-400 border border-dark-border rounded-2xl">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-purple-400" />
              Introspeccionando esquema físico de la base de datos...
            </div>
          ) : filteredDictTables.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-dark-border rounded-2xl p-8 space-y-2">
              <Database className="w-8 h-8 text-gray-500 mx-auto" />
              <h4 className="text-sm font-semibold text-white">No se encontraron tablas físicas</h4>
              <p className="text-xs text-gray-400">
                Asegúrate de que haya una base de datos conectada o importa un archivo SQLite en la pestaña de Conexiones.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredDictTables.map((tbl: DataDictionaryTable) => {
                const isExpanded = Boolean(expandedTables[tbl.table_name]);
                return (
                  <div
                    key={tbl.table_name}
                    className="glass-card rounded-2xl border border-white/10 overflow-hidden transition-colors"
                  >
                    {/* Table Summary Header */}
                    <div
                      onClick={() => toggleTableExpansion(tbl.table_name)}
                      className="p-4 bg-dark-surface/80 hover:bg-dark-card/60 flex items-center justify-between cursor-pointer transition-colors border-b border-dark-border/60"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
                          <TableIcon className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-white text-sm font-mono">{tbl.table_name}</span>
                            <span className="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full font-semibold">
                              {tbl.column_count} Columnas
                            </span>
                            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                              {tbl.row_count.toLocaleString()} Filas
                            </span>
                          </div>
                          {tbl.description && (
                            <p className="text-xs text-gray-400 mt-0.5">{tbl.description}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 text-xs text-gray-400">
                        <span>{isExpanded ? 'Ocultar Columnas' : 'Ver Columnas'}</span>
                        <Eye className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      </div>
                    </div>

                    {/* Columns Detail Table */}
                    {isExpanded && (
                      <div className="overflow-x-auto p-2 bg-dark-base/40">
                        <table className="w-full text-left text-xs min-w-[700px]">
                          <thead className="text-[10px] text-gray-400 uppercase tracking-wider border-b border-dark-border">
                            <tr>
                              <th className="px-3 py-2">Columna</th>
                              <th className="px-3 py-2">Tipo SQL</th>
                              <th className="px-3 py-2">Restricciones</th>
                              <th className="px-3 py-2">Muestra de Datos Reales</th>
                              <th className="px-3 py-2">Definición de Negocio (IA)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-dark-border/50 text-gray-300">
                            {tbl.columns.map((col) => (
                              <tr key={col.name} className="hover:bg-dark-card/30 transition-colors">
                                <td className="px-3 py-2.5 font-mono font-medium text-white flex items-center space-x-1.5">
                                  {col.is_pk && <Key className="w-3 h-3 text-amber-400 shrink-0" />}
                                  <span>{col.name}</span>
                                </td>
                                <td className="px-3 py-2.5">
                                  <span className="bg-dark-card border border-dark-border text-cyan-400 font-mono px-2 py-0.5 rounded text-[10px] font-semibold">
                                    {col.data_type}
                                  </span>
                                </td>
                                <td className="px-3 py-2.5">
                                  <div className="flex items-center space-x-1 text-[10px]">
                                    {col.is_pk && (
                                      <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded font-bold">
                                        PK
                                      </span>
                                    )}
                                    {!col.is_nullable && (
                                      <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1.5 py-0.5 rounded">
                                        NOT NULL
                                      </span>
                                    )}
                                    {col.is_nullable && !col.is_pk && (
                                      <span className="text-gray-500">NULL</span>
                                    )}
                                  </div>
                                </td>
                                <td className="px-3 py-2.5 max-w-xs">
                                  {col.sample_values && col.sample_values.length > 0 ? (
                                    <div className="flex flex-wrap gap-1">
                                      {col.sample_values.map((v, i) => (
                                        <span
                                          key={i}
                                          className="bg-dark-card/80 text-gray-300 font-mono text-[10px] px-1.5 py-0.5 rounded border border-dark-border/60 truncate max-w-[140px]"
                                          title={v}
                                        >
                                          {v}
                                        </span>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-gray-600 text-[10px] italic">Sin datos</span>
                                  )}
                                </td>
                                <td className="px-3 py-2.5 text-gray-300">
                                  {col.description ? (
                                    <div>
                                      <span className="text-white font-medium text-[11px] block">
                                        {col.friendly_name || col.name}
                                      </span>
                                      <span className="text-gray-400 text-[11px]">{col.description}</span>
                                    </div>
                                  ) : (
                                    <span className="text-gray-500 italic text-[11px]">
                                      Sin descripción semántica
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
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
