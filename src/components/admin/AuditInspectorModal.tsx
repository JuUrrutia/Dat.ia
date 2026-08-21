import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle, X, Copy, Check } from 'lucide-react';
import { AuditLog } from '../../types';

interface AuditInspectorModalProps {
  log: AuditLog | null;
  onClose: () => void;
}

export const AuditStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const s = status.toUpperCase();
  if (s.includes('APROBADO')) {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <CheckCircle2 className="w-3.5 h-3.5" />
        <span>Aprobado</span>
      </span>
    );
  }
  if (s.includes('RECHAZADO')) {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <XCircle className="w-3.5 h-3.5" />
        <span>Bloqueado RBAC</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
      <AlertTriangle className="w-3.5 h-3.5" />
      <span>{status}</span>
    </span>
  );
};

export const AuditInspectorModal: React.FC<AuditInspectorModalProps> = ({ log, onClose }) => {
  const [sqlCopied, setSqlCopied] = useState(false);

  if (!log) return null;

  const handleCopySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    setSqlCopied(true);
    setTimeout(() => setSqlCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <div>
              <h4 className="text-sm font-bold text-white">
                Inspección de Auditoría - Evento #{log.id}
              </h4>
              <p className="text-xs text-gray-400">
                {new Date(log.timestamp).toLocaleString()} • {log.username} ({log.user_role})
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal de auditoría"
            className="text-gray-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <span className="text-gray-400 font-semibold uppercase text-[10px] tracking-wider">
              Pregunta en Lenguaje Natural:
            </span>
            <div className="p-3 bg-dark-base rounded-xl border border-dark-border text-white mt-1">
              {log.question_prompt}
            </div>
          </div>

          {log.sql_generated ? (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-gray-400 font-semibold uppercase text-[10px] tracking-wider">
                  SQL Generado & Validado por AST Guardrail:
                </span>
                <button
                  type="button"
                  onClick={() => handleCopySql(log.sql_generated || '')}
                  aria-label="Copiar SQL de auditoría"
                  className="flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 transition-colors"
                >
                  {sqlCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Copiado</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copiar SQL</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3 bg-dark-base rounded-xl border border-dark-border text-emerald-400 font-mono overflow-x-auto whitespace-pre-wrap">
                {log.sql_generated}
              </pre>
            </div>
          ) : (
            <div className="p-3 bg-dark-base rounded-xl border border-dark-border text-gray-500 italic">
              No se generó consulta SQL para esta interacción (ej. conversación general o bloqueo previo).
            </div>
          )}

          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-dark-base border border-dark-border">
              <span className="text-gray-500 text-[10px] uppercase font-semibold">Estado Validación</span>
              <div className="mt-1">
                <AuditStatusBadge status={log.validation_status} />
              </div>
            </div>
            <div className="p-3 rounded-xl bg-dark-base border border-dark-border">
              <span className="text-gray-500 text-[10px] uppercase font-semibold">Latencia Ejecución</span>
              <div className="mt-1 text-white font-mono font-semibold">{log.execution_time_ms} ms</div>
            </div>
            <div className="p-3 rounded-xl bg-dark-base border border-dark-border">
              <span className="text-gray-500 text-[10px] uppercase font-semibold">Filas Devueltas</span>
              <div className="mt-1 text-white font-mono font-semibold">{log.rows_returned}</div>
            </div>
          </div>

          {log.error_message && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              <strong className="block font-semibold mb-0.5">Mensaje de Diagnóstico / Error:</strong>
              <span>{log.error_message}</span>
            </div>
          )}
        </div>

        <div className="pt-3 flex justify-end border-t border-dark-border">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
