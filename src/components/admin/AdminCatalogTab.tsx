import React from 'react';
import { Sparkles, Check, Plus, BookOpen, Database, RefreshCw, HardDrive, AlertCircle } from 'lucide-react';
import { CatalogEditModal } from './CatalogEditModal';
import { CatalogAddModal } from './CatalogAddModal';
import { SemanticCatalogSection } from './catalog/SemanticCatalogSection';
import { DataDictionarySection } from './catalog/DataDictionarySection';
import { useAdminCatalog } from '../../features/admin/hooks/useAdminCatalog';

interface AdminCatalogTabProps {
  catalog?: any[];
  aiEnriching?: boolean;
  aiSuccess?: boolean;
  onRunAiCatalog?: () => void;
}

export const AdminCatalogTab: React.FC<AdminCatalogTabProps> = () => {
  const {
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
    refreshAll,
  } = useAdminCatalog();

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

      {/* Database Connection Selector Toolbar */}
      {connectors.length > 0 && (
        <div className="bg-dark-base/80 p-3 rounded-2xl border border-dark-border flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs text-gray-300">
            <Database className="w-4 h-4 text-purple-400 shrink-0" />
            <span className="font-semibold text-white whitespace-nowrap">Fuente de Datos:</span>
            <span className="text-gray-400 text-[11px] hidden sm:inline">
              Selecciona la base de datos a inspeccionar
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {connectors.map((c) => {
              const isSelected = c.id === selectedConnectionId;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleSelectConnection(c.id)}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs transition-all ${
                    isSelected
                      ? 'bg-purple-600/20 text-purple-300 border border-purple-500/50 shadow-sm shadow-purple-500/20 font-bold'
                      : 'bg-dark-card/60 text-gray-400 hover:text-white hover:bg-dark-card border border-dark-border font-medium'
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      c.is_active ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-gray-500'
                    }`}
                  />
                  <span className="truncate max-w-[150px] sm:max-w-[200px]">{c.name}</span>
                  <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 bg-dark-base rounded text-gray-400">
                    {c.db_type}
                  </span>
                  {c.is_uploaded && (
                    <span title="Archivo importado">
                      <HardDrive className="w-3 h-3 text-cyan-400 shrink-0" />
                    </span>
                  )}
                </button>
              );
            })}

            <button
              type="button"
              onClick={refreshAll}
              className="p-1.5 text-gray-400 hover:text-white bg-dark-card/40 hover:bg-dark-card rounded-xl border border-dark-border transition-colors"
              title="Refrescar fuentes y esquemas"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingConnectors ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      )}

      {enrichSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4 shrink-0" />
          <span>{enrichSuccessMsg}</span>
        </div>
      )}

      {enrichErrorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{enrichErrorMsg}</span>
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
        connectionName={selectedConnector?.name}
        connectionId={selectedConnectionId ?? undefined}
      />
    </div>
  );
};
