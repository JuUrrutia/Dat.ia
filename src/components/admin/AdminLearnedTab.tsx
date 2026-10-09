import React, { useState } from 'react';
import { BrainCircuit, RefreshCw, Trash2, AlertTriangle, X, Star } from 'lucide-react';
import { GoldenQuery } from '../../features/admin/services/learning_memory_service';
import { useAdminLearned } from '../../features/admin/hooks/useAdminLearned';
import { useModalA11y } from '../../hooks/useModalA11y';

/** Cuanto SQL se ve en la celda antes de truncar. El `title` lleva el completo. */
const SQL_PREVIEW_CHARS = 90;

/**
 * Memoria de aprendizaje de la conexion: lo que el motor se esta inyectando como
 * few-shot en el prompt de TODOS los usuarios.
 *
 * Es una pantalla de inspeccion y revocacion, no de edicion: el recurso es
 * compartido (la tabla no tiene `user_id`) asi que un SQL equivocado afecta a
 * toda la empresa. Marcar/desmarcar golden ya existe por POST; lo unico que
 * faltaba era poder VER lo que hay y BORRARLO.
 */
export const AdminLearnedTab: React.FC = () => {
  const {
    connectors,
    selectedConnectionId,
    selectedConnector,
    handleSelectConnection,
    items,
    isLoading,
    loaded,
    error,
    actionError,
    deletingId,
    deleteItem,
    refresh,
  } = useAdminLearned();

  const [pendingDelete, setPendingDelete] = useState<GoldenQuery | null>(null);
  const confirmRef = useModalA11y<HTMLDivElement>(Boolean(pendingDelete), () =>
    setPendingDelete(null)
  );

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const ok = await deleteItem(pendingDelete.id);
    if (ok) setPendingDelete(null);
  };

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 border border-slate-200 dark:border-white/10 space-y-5 bg-white dark:bg-zinc-900/90 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-dark-border pb-4">
        <div className="space-y-1">
          <h3 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-brand-600 dark:text-purple-400" />
            Memoria de Aprendizaje de la IA
          </h3>
          <p className="text-xs text-slate-600 dark:text-gray-400">
            Consultas que el motor reutiliza como ejemplo en el prompt. Son compartidas: un SQL mal enseñado afecta a
            todos los usuarios de la fuente.
          </p>
        </div>

        <button
          type="button"
          onClick={refresh}
          className="p-2 text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-dark-card/40 hover:bg-slate-200 dark:hover:bg-dark-card rounded-xl border border-slate-200 dark:border-dark-border transition-colors cursor-pointer self-start"
          title="Refrescar memoria de aprendizaje"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Selector de conexion: mismo control que en Permisos, porque el
          aislamiento de la memoria es por conexion. */}
      {connectors.length > 0 && (
        <div className="bg-slate-50 dark:bg-dark-base/80 p-3 rounded-2xl border border-slate-200 dark:border-dark-border flex flex-col md:flex-row md:items-center justify-between gap-3">
          <span className="text-xs font-semibold text-slate-900 dark:text-white whitespace-nowrap">Fuente de Datos:</span>
          <div className="flex flex-wrap items-center gap-2">
            {connectors.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => handleSelectConnection(c.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs transition-all ${
                  c.id === selectedConnectionId
                    ? 'bg-brand-50 text-brand-700 border border-brand-300 dark:bg-purple-600/20 dark:text-purple-300 dark:border-purple-500/50 shadow-xs font-bold'
                    : 'bg-white dark:bg-dark-card/60 text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-dark-card border border-slate-200 dark:border-dark-border font-medium'
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    c.is_active ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-slate-400 dark:bg-gray-500'
                  }`}
                />
                <span className="truncate max-w-[150px] sm:max-w-[200px]">{c.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{actionError}</span>
        </div>
      )}

      {isLoading && (
        <p className="text-xs text-slate-500 dark:text-gray-400">Cargando memoria de aprendizaje del servidor...</p>
      )}

      {loaded && !error && items.length === 0 && !isLoading && (
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-dark-base/80 border border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 text-xs">
          El servidor no reportó consultas aprendidas para «{selectedConnector?.name ?? 'esta fuente'}». Mientras esté
          vacía, el chat no recibe ejemplos few-shot de esta conexión.
        </div>
      )}

      {items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-dark-border">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-dark-base border-b border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 whitespace-nowrap">Patrón de pregunta</th>
                <th className="px-4 py-3 whitespace-nowrap">SQL aprendido</th>
                <th className="px-3 py-3 whitespace-nowrap">Rol</th>
                <th className="px-3 py-3 whitespace-nowrap text-center">Veces usada</th>
                <th className="px-3 py-3 whitespace-nowrap text-center">Dorada</th>
                <th className="px-3 py-3 text-right whitespace-nowrap">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-dark-border text-slate-800 dark:text-gray-200 bg-white dark:bg-transparent">
              {items.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-dark-card/50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white max-w-[260px]">
                    <span className="block truncate" title={m.question_pattern}>
                      {m.question_pattern}
                    </span>
                    {m.was_self_healed && (
                      <span className="text-[10px] text-cyan-600 dark:text-cyan-400">reparada sola</span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[380px]">
                    <code
                      className="block truncate font-mono text-[11px] text-slate-600 dark:text-gray-300"
                      title={m.successful_sql}
                    >
                      {m.successful_sql.length > SQL_PREVIEW_CHARS
                        ? `${m.successful_sql.slice(0, SQL_PREVIEW_CHARS)}…`
                        : m.successful_sql}
                    </code>
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap text-slate-600 dark:text-gray-400">
                    {m.user_role || '—'}
                  </td>
                  <td className="px-3 py-3 text-center font-mono text-slate-900 dark:text-white">
                    {m.execution_count}
                  </td>
                  <td className="px-3 py-3 text-center">
                    {m.is_golden ? (
                      <Star
                        className="w-3.5 h-3.5 inline text-amber-500 dark:text-amber-400"
                        aria-label="Consulta maestra"
                      />
                    ) : (
                      <span className="text-slate-400 dark:text-gray-600" aria-label="No es maestra">
                        —
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => setPendingDelete(m)}
                      disabled={deletingId === m.id}
                      aria-label={`Eliminar memoria aprendida: ${m.question_pattern}`}
                      title="Eliminar de la memoria compartida"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:text-gray-400 dark:hover:text-rose-400 dark:hover:bg-rose-500/15 border border-transparent hover:border-rose-500/30 transition-all focus-visible:ring-2 focus-visible:ring-rose-500 disabled:opacity-50 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirmacion: borrar quita el SQL del prompt de toda la conexion. */}
      {pendingDelete && (
        <div
          ref={confirmRef}
          role="dialog"
          aria-modal="true"
          aria-label="Confirmar borrado de memoria aprendida"
          tabIndex={-1}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn"
        >
          <div className="glass-panel w-full max-w-md rounded-2xl border border-white/10 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-dark-border pb-3">
              <h4 className="text-sm font-bold text-app-text flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-rose-400" />
                Eliminar memoria de aprendizaje
              </h4>
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                aria-label="Cerrar confirmacion"
                className="text-gray-400 hover:text-app-text p-1 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-300 leading-relaxed">
              Esta consulta deja de inyectarse como ejemplo en el prompt de todos los usuarios de «
              {selectedConnector?.name ?? 'esta fuente'}». No se puede deshacer.
            </p>
            <code className="block truncate font-mono text-[11px] text-gray-400" title={pendingDelete.successful_sql}>
              {pendingDelete.question_pattern}
            </code>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                className="px-4 py-2 rounded-xl bg-dark-card text-gray-300 text-xs font-medium hover:bg-dark-border transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={deletingId === pendingDelete.id}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{deletingId === pendingDelete.id ? 'Eliminando...' : 'Eliminar para todos'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};