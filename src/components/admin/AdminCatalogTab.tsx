import React, { useReducer } from 'react';
import { Sparkles, Check, Search, Plus, Edit3, BookOpen } from 'lucide-react';
import { CatalogEditModal } from './CatalogEditModal';
import { CatalogAddModal } from './CatalogAddModal';

export interface CatalogItem {
  table: string;
  column: string;
  desc: string;
  formula: string;
  is_ai: boolean;
}

interface AdminCatalogTabProps {
  catalog: CatalogItem[];
  aiEnriching: boolean;
  aiSuccess: boolean;
  onRunAiCatalog: () => void;
}

interface CatalogState {
  items: CatalogItem[];
  searchQuery: string;
  selectedTableFilter: string;
  editingItem: CatalogItem | null;
  isAddModalOpen: boolean;
}

type CatalogAction =
  | { type: 'SET_ITEMS'; items: CatalogItem[] }
  | { type: 'SET_SEARCH'; query: string }
  | { type: 'SET_TABLE_FILTER'; filter: string }
  | { type: 'OPEN_EDIT'; item: CatalogItem }
  | { type: 'CLOSE_EDIT' }
  | { type: 'OPEN_ADD' }
  | { type: 'CLOSE_ADD' };

const STORAGE_KEY = 'datia_semantic_catalog:v1';
const LEGACY_STORAGE_KEY = 'datia_semantic_catalog';

function loadInitialCatalog(fallback: CatalogItem[]): CatalogItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {}
  return fallback || [];
}

function catalogReducer(state: CatalogState, action: CatalogAction): CatalogState {
  switch (action.type) {
    case 'SET_ITEMS':
      return { ...state, items: action.items };
    case 'SET_SEARCH':
      return { ...state, searchQuery: action.query };
    case 'SET_TABLE_FILTER':
      return { ...state, selectedTableFilter: action.filter };
    case 'OPEN_EDIT':
      return { ...state, editingItem: action.item };
    case 'CLOSE_EDIT':
      return { ...state, editingItem: null };
    case 'OPEN_ADD':
      return { ...state, isAddModalOpen: true };
    case 'CLOSE_ADD':
      return { ...state, isAddModalOpen: false };
    default:
      return state;
  }
}

export const AdminCatalogTab: React.FC<AdminCatalogTabProps> = ({
  catalog,
  aiEnriching,
  aiSuccess,
  onRunAiCatalog,
}) => {
  const [state, dispatch] = useReducer(catalogReducer, undefined, () => ({
    items: loadInitialCatalog(catalog),
    searchQuery: '',
    selectedTableFilter: 'ALL',
    editingItem: null,
    isAddModalOpen: false,
  }));

  const saveCatalogToStorage = (updatedItems: CatalogItem[]) => {
    dispatch({ type: 'SET_ITEMS', items: updatedItems });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedItems));
    } catch {}
  };

  const uniqueTables = Array.from(new Set(state.items.map((i) => i.table)));

  const filteredItems = state.items.filter((cat) => {
    const matchesSearch =
      cat.table.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      cat.column.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      cat.desc.toLowerCase().includes(state.searchQuery.toLowerCase());
    const matchesTable = state.selectedTableFilter === 'ALL' || cat.table === state.selectedTableFilter;
    return matchesSearch && matchesTable;
  });

  const handleSaveEdit = (desc: string, formula: string) => {
    if (!state.editingItem) return;
    const updated = state.items.map((i) =>
      i.table === state.editingItem?.table && i.column === state.editingItem?.column
        ? { ...i, desc, formula }
        : i
    );
    saveCatalogToStorage(updated);
    dispatch({ type: 'CLOSE_EDIT' });
  };

  const handleAddItem = (newItem: CatalogItem) => {
    const updated = [newItem, ...state.items];
    saveCatalogToStorage(updated);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" /> Catálogo Semántico y Diccionario de Datos (IA)
          </h3>
          <p className="text-xs text-gray-400">
            Define descripciones en lenguaje natural y reglas de gobernanza para el modelo Qwen2.5-Coder
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => dispatch({ type: 'OPEN_ADD' })}
            className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-gray-200 border border-dark-border px-3.5 py-2 rounded-xl transition-colors font-medium"
          >
            <Plus className="w-4 h-4" />
            <span>Añadir Regla</span>
          </button>

          <button
            type="button"
            onClick={onRunAiCatalog}
            disabled={aiEnriching}
            className="flex items-center space-x-2 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
          >
            <Sparkles className={`w-4 h-4 ${aiEnriching ? 'animate-spin' : ''}`} />
            <span>{aiEnriching ? 'Analizando Esquema...' : 'Auto-enriquecer con IA'}</span>
          </button>
        </div>
      </div>

      {aiSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4" />
          <span>Catálogo semántico enriquecido automáticamente con descripciones generadas por la IA local.</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <label htmlFor="catalog-search" className="sr-only">
            Buscar en catálogo
          </label>
          <input
            id="catalog-search"
            aria-label="Buscar tabla, campo o descripción"
            type="text"
            value={state.searchQuery}
            onChange={(e) => dispatch({ type: 'SET_SEARCH', query: e.target.value })}
            placeholder="Buscar tabla, campo o descripción..."
            className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
          />
        </div>

        <div className="flex items-center space-x-2 text-xs w-full sm:w-auto">
          <label htmlFor="catalog-table-filter" className="text-gray-400 font-medium whitespace-nowrap">
            Filtrar por tabla:
          </label>
          <select
            id="catalog-table-filter"
            aria-label="Filtrar por tabla"
            value={state.selectedTableFilter}
            onChange={(e) => dispatch({ type: 'SET_TABLE_FILTER', filter: e.target.value })}
            className="bg-dark-base border border-dark-border rounded-xl px-3 py-1.5 text-white focus:outline-none focus:border-purple-500 text-xs"
          >
            <option value="ALL">Todas las Tablas ({state.items.length})</option>
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
        <table className="w-full text-left text-xs">
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
            {filteredItems.map((cat) => (
              <tr key={`${cat.table}-${cat.column}`} className="hover:bg-dark-card/50 transition-colors">
                <td className="px-4 py-3 font-mono font-semibold text-purple-400">{cat.table}</td>
                <td className="px-4 py-3 font-mono font-medium text-white">{cat.column}</td>
                <td className="px-4 py-3 text-gray-300 max-w-md">{cat.desc}</td>
                <td className="px-4 py-3 font-mono text-gray-400 text-[11px]">{cat.formula}</td>
                <td className="px-4 py-3">
                  {cat.is_ai ? (
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
                  <button
                    type="button"
                    onClick={() => dispatch({ type: 'OPEN_EDIT', item: cat })}
                    aria-label={`Editar regla para ${cat.table}.${cat.column}`}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 transition-colors ml-auto"
                    title="Editar Regla"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit Rule Modal */}
      <CatalogEditModal
        isOpen={Boolean(state.editingItem)}
        item={state.editingItem}
        onClose={() => dispatch({ type: 'CLOSE_EDIT' })}
        onSave={handleSaveEdit}
      />

      {/* Add New Rule Modal */}
      <CatalogAddModal
        isOpen={state.isAddModalOpen}
        onClose={() => dispatch({ type: 'CLOSE_ADD' })}
        onAdd={handleAddItem}
      />
    </div>
  );
};
