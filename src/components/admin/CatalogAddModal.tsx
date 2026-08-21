import React, { useState } from 'react';
import { X, BookOpen } from 'lucide-react';
import { CatalogItem } from './AdminCatalogTab';

interface CatalogAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: CatalogItem) => void;
}

export const CatalogAddModal: React.FC<CatalogAddModalProps> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  const [formTable, setFormTable] = useState('');
  const [formColumn, setFormColumn] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formFormula, setFormFormula] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTable.trim() || !formColumn.trim() || !formDesc.trim()) return;

    onAdd({
      table: formTable.trim(),
      column: formColumn.trim(),
      desc: formDesc.trim(),
      formula: formFormula.trim() || 'MANUAL_RULE',
      is_ai: false,
    });

    setFormTable('');
    setFormColumn('');
    setFormDesc('');
    setFormFormula('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-400" /> Nueva Regla Semántica
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
            <label htmlFor="catalog-add-table" className="block text-gray-300 font-medium mb-1">
              Nombre de Tabla
            </label>
            <input
              id="catalog-add-table"
              aria-label="Nombre de Tabla"
              type="text"
              value={formTable}
              onChange={(e) => setFormTable(e.target.value)}
              placeholder="ej. Answer o fact_ventas"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 font-mono"
              required
            />
          </div>

          <div>
            <label htmlFor="catalog-add-column" className="block text-gray-300 font-medium mb-1">
              Nombre de Columna / Campo
            </label>
            <input
              id="catalog-add-column"
              aria-label="Nombre de Columna / Campo"
              type="text"
              value={formColumn}
              onChange={(e) => setFormColumn(e.target.value)}
              placeholder="ej. AnswerText o monto_total"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500 font-mono"
              required
            />
          </div>

          <div>
            <label htmlFor="catalog-add-desc" className="block text-gray-300 font-medium mb-1">
              Descripción Semántica
            </label>
            <textarea
              id="catalog-add-desc"
              aria-label="Descripción Semántica"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              placeholder="Explicación de qué representa este campo para que la IA elija la columna correcta..."
              rows={3}
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-white focus:outline-none focus:border-purple-500"
              required
            />
          </div>

          <div>
            <label htmlFor="catalog-add-formula" className="block text-gray-300 font-medium mb-1">
              Fórmula o Regla (Opcional)
            </label>
            <input
              id="catalog-add-formula"
              aria-label="Fórmula o Regla (Opcional)"
              type="text"
              value={formFormula}
              onChange={(e) => setFormFormula(e.target.value)}
              placeholder="ej. SUM(monto) / MASKED / TEXT_LITERAL"
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
              className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
            >
              Añadir al Catálogo
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
