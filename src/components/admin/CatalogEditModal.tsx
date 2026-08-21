import React, { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import { CatalogItem } from './AdminCatalogTab';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <h4 className="text-sm font-bold text-white">
            Editar Regla Semántica: {item.table}.{item.column}
          </h4>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
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

          <div className="pt-3 flex justify-end space-x-2 border-t border-dark-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs hover:bg-dark-border transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex items-center space-x-1 bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Guardar Cambios</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
