import React, { useState } from 'react';
import { TraceabilityAudit } from '../../types';
import { CheckCircle2, ShieldCheck, Clock, Database, Copy, Check, Info, Code2, Layers } from 'lucide-react';

interface TraceabilityModalProps {
  traceability: TraceabilityAudit;
  isOpen: boolean;
  onClose: () => void;
}

export const TraceabilityModal: React.FC<TraceabilityModalProps> = ({ traceability, isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopySQL = () => {
    navigator.clipboard.writeText(traceability.sql_executed);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-3xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Panel de Trazabilidad & Auditoría</h3>
              <p className="text-xs text-gray-400">Inspección de consulta, AST Guardrail y diccionario semántico</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-dark-card transition-all"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Status Bar Badges */}
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-dark-base/60 p-3 rounded-xl border border-dark-border flex items-center space-x-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <div>
                <div className="text-[10px] text-gray-400 uppercase">Validación AST</div>
                <div className="text-xs font-semibold text-emerald-400">{traceability.validation_status}</div>
              </div>
            </div>

            <div className="bg-dark-base/60 p-3 rounded-xl border border-dark-border flex items-center space-x-3">
              <Clock className="w-5 h-5 text-brand-400" />
              <div>
                <div className="text-[10px] text-gray-400 uppercase">Latencia BD</div>
                <div className="text-xs font-semibold text-white">{traceability.execution_time_ms} ms</div>
              </div>
            </div>

            <div className="bg-dark-base/60 p-3 rounded-xl border border-dark-border flex items-center space-x-3">
              <Database className="w-5 h-5 text-indigo-400" />
              <div>
                <div className="text-[10px] text-gray-400 uppercase">Filas Devueltas</div>
                <div className="text-xs font-semibold text-white">{traceability.rows_returned} registros</div>
              </div>
            </div>

            <div className="bg-dark-base/60 p-3 rounded-xl border border-dark-border flex items-center space-x-3">
              <Layers className="w-5 h-5 text-purple-400" />
              <div>
                <div className="text-[10px] text-gray-400 uppercase">Tablas Usadas</div>
                <div className="text-xs font-semibold text-white">{traceability.schema_tables_used.length} tablas</div>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-dark-card/40 p-4 rounded-xl border border-dark-border space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-gray-300">
              <Info className="w-4 h-4 text-brand-400" />
              <span>Metodología de Cálculo & Diccionario de Datos</span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">{traceability.explanation}</p>
          </div>

          {/* Executed SQL Box */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-semibold text-gray-300">
                <Code2 className="w-4 h-4 text-brand-400" />
                <span>Sentencia SQL Auditada (Ejecutada en Modo SOLO LECTURA)</span>
              </div>
              <button
                onClick={handleCopySQL}
                className="flex items-center space-x-1 text-xs text-brand-400 hover:text-brand-300 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 px-3 py-1 rounded-lg transition-all"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copiado' : 'Copiar SQL'}</span>
              </button>
            </div>
            <pre className="bg-dark-base p-4 rounded-xl border border-dark-border font-mono text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap">
              {traceability.sql_executed}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-dark-border bg-dark-surface/60 flex items-center justify-between text-xs text-gray-400">
          <span>Gobernanza RBAC: Inyección de esquema dinámico y filtro AST activo</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-dark-card hover:bg-dark-border text-white text-xs font-medium transition-all"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
