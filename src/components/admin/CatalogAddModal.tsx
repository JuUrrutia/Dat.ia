import React, { useState } from 'react';
import { X, BookOpen, Database, AlertCircle } from 'lucide-react';
import { CatalogItem } from './CatalogEditModal';
import { useModalA11y } from '../../hooks/useModalA11y';

interface CatalogAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (item: CatalogItem) => Promise<boolean> | boolean;
  connectionName?: string;
  connectionId?: number;
  errorMsg?: string | null;
}

export const CatalogAddModal: React.FC<CatalogAddModalProps> = ({
  isOpen,
  onClose,
  onAdd,
  connectionName,
  connectionId,
  errorMsg,
}) => {
  const [formTable, setFormTable] = useState('');
  const [formColumn, setFormColumn] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formFormula, setFormFormula] = useState('');

  // Dialog semantics, Escape, focus containment and focus restore.
  const modalRef = useModalA11y<HTMLDivElement>(isOpen, onClose);

  if (!isOpen) return null;

  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTable.trim() || !formColumn.trim() || !formDesc.trim()) return;
    if (isSaving) return;
    setIsSaving(true);
    try {
      // Awaited: this used to be fire-and-forget followed by an unconditional
      // onClose(), so a 400 closed the modal, the typed table/column/description
      // was gone, and the error only surfaced as a banner on the tab behind.
      // Empty formula, not the 'MANUAL_RULE' sentinel, which the table used to
      // render verbatim in the "Fórmula / Regla" column and the text-to-SQL
      // engine received as a rule.
      const ok = await onAdd({
        table: formTable.trim(),
        column: formColumn.trim(),
        desc: formDesc.trim(),
        formula: formFormula.trim(),
        is_ai: false,
        connection_id: connectionId,
      } as any);

      if (!ok) return;

      setFormTable('');
      setFormColumn('');
      setFormDesc('');
      setFormFormula('');
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Agregar regla de catálogo" tabIndex={-1} className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-md rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[88vh] sm:max-h-[90vh]">
        {/* Header */}
        <div className="shrink-0 px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <div className="space-y-0.5">
            <h4 className="text-sm font-bold text-app-text flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-purple-400" /> Nueva Regla Semántica
            </h4>
            {connectionName && (
              <div className="flex items-center gap-1.5 text-[11px] text-purple-300">
                <Database className="w-3 h-3 text-purple-400" />
                <span>Base de Datos: <strong className="text-app-text font-medium">{connectionName}</strong></span>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-app-text p-1 rounded-lg hover:bg-dark-card transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form id="catalog-add-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6 space-y-3.5 text-xs">
          {errorMsg && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start space-x-2" role="alert">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500 font-mono"
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500 font-mono"
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500"
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
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3 py-2 text-app-text focus:outline-none focus:border-purple-500 font-mono"
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
            form="catalog-add-form"
            type="submit"
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors"
          >
            Añadir al Catálogo
          </button>
        </div>
      </div>
    </div>
  );
};
