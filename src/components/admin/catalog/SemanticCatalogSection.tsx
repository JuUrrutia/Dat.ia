import React, { useState } from 'react';
import { Search, RefreshCw, Edit3, Trash2 } from 'lucide-react';
import { CatalogItem } from '../../../services/catalog_service';

interface SemanticCatalogSectionProps {
  items: CatalogItem[];
  isLoadingCatalog: boolean;
  onOpenEditModal: (item: CatalogItem) => void;
  onDeleteItem: (id: number, table: string, column?: string) => void;
}

export const SemanticCatalogSection: React.FC<SemanticCatalogSectionProps> = ({
  items,
  isLoadingCatalog,
  onOpenEditModal,
  onDeleteItem,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTableFilter, setSelectedTableFilter] = useState('ALL');

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

  return (
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
                        onClick={() => onOpenEditModal(cat)}
                        aria-label={`Editar regla para ${cat.table_name}.${cat.column_name || 'tabla'}`}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 transition-colors"
                        title="Editar Regla"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => onDeleteItem(cat.id, cat.table_name, cat.column_name)}
                        aria-label={`Eliminar regla ${cat.table_name}.${cat.column_name || 'tabla'}`}
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
  );
};
