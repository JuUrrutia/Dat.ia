import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';

export interface CatalogItem {
  id?: number;
  table: string;
  column: string;
  desc: string;
  formula: string;
  is_ai: boolean;
}

interface CatalogEditModalProps {
  isOpen: boolean;
  item: CatalogItem | null;
  onClose: () => void;
  onSave: (desc: string, formula: string) => void;
}

export const CatalogEditModal: React.FC<CatalogEditModalProps> = ({
  isOpen,
  item,
  onClose,
  onSave,
}) => {
  const [formDesc, setFormDesc] = useState('');
  const [formFormula, setFormFormula] = useState('');

  useEffect(() => {
    if (item) {
      setFormDesc(item.desc);
      setFormFormula(item.formula);
    }
  }, [item]);

  if (!isOpen || !item) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formDesc, formFormula);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[88vh] sm:max-h-[90vh]">
        {/* Header */}
        <div className="shrink-0 px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <h4 className="text-sm font-bold text-white truncate">
            Editar Regla Semántica: {item.table}.{item.column}
          </h4>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-dark-card transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form id="catalog-edit-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6 space-y-3.5 text-xs">
          <div>
            <label htmlFor="catalog-edit-desc" className="block text-gray-300 font-medium mb-1">
              Descripción Semántica (para LLM)
            </label>
            <textarea
              id="catalog-edit-desc"
              aria-label="Descripción Semántica (para LLM)"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              rows={3}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500"
              required
            />
          </div>

          <div>
            <label htmlFor="catalog-edit-formula" className="block text-gray-300 font-medium mb-1">
              Fórmula o Regla de Cálculo
            </label>
            <input
              id="catalog-edit-formula"
              aria-label="Fórmula o Regla de Cálculo"
              type="text"
              value={formFormula}
              onChange={(e) => setFormFormula(e.target.value)}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 font-mono"
            />
          </div>
        </form>

        {/* Fixed Sticky Footer Actions */}
        <div className="shrink-0 px-5 sm:px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex justify-end space-x-2 z-10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs hover:bg-dark-border transition-colors"
          >
            Cancelar
          </button>
          <button
            form="catalog-edit-form"
            type="submit"
            className="flex items-center space-x-1 bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Guardar Cambios</span>
          </button>
        </div>
      </div>
    </div>
  );
};
