import React from 'react';
import {
  ShieldCheck,
  Database,
  RefreshCw,
  Save,
  AlertTriangle,
  Check,
  Lock,
  HardDrive,
} from 'lucide-react';
import { useAdminPermissions } from '../../features/admin/hooks/useAdminPermissions';

/**
 * Matriz rol × tabla del permiso de acceso (default-deny).
 *
 * Solo existe para admin: `GET`/`PUT /permissions` son `get_current_admin`. Si el
 * rol no es admin, el backend responde 403 y esta pantalla no se monta — el
 * guard esta en `AdminPage`, no acá adentro.
 */
export const AdminPermissionsTab: React.FC = () => {
  const {
    connectors,
    selectedConnectionId,
    selectedConnector,
    handleSelectConnection,
    isLoadingPermissions,
    permissionsLoaded,
    permissionsError,
    roles,
    rolesLoaded,
    rolesError,
    tables,
    isChecked,
    grantedByAdmin,
    toggleCell,
    grantAllToRole,
    revokeAllFromRole,
    pendingCount,
    savePending,
    isSaving,
    saveError,
    saveSuccessMsg,
    refresh,
  } = useAdminPermissions();

  const needsReview = Boolean(selectedConnector?.requires_permission_review);

  return (
    <div className="glass-panel rounded-2xl sm:rounded-3xl p-4 sm:p-6 border border-slate-200 dark:border-white/10 space-y-5 bg-white dark:bg-zinc-900/90 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-dark-border pb-4">
        <div className="space-y-1">
          <h3 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-600 dark:text-purple-400" />
            Permisos de Acceso a Tablas (Rol × Tabla)
          </h3>
          <p className="text-xs text-slate-600 dark:text-gray-400">
            Política default-deny: al subir un dataset ningún rol obtiene acceso hasta que lo concedas acá
          </p>
        </div>

        <button
          type="button"
          onClick={refresh}
          className="p-2 text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-dark-card/40 hover:bg-slate-200 dark:hover:bg-dark-card rounded-xl border border-slate-200 dark:border-dark-border transition-colors cursor-pointer self-start"
          title="Refrescar matriz de permisos"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoadingPermissions ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Selector de conector */}
      {connectors.length > 0 && (
        <div className="bg-slate-50 dark:bg-dark-base/80 p-3 rounded-2xl border border-slate-200 dark:border-dark-border flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs text-slate-700 dark:text-gray-300">
            <Database className="w-4 h-4 text-brand-600 dark:text-purple-400 shrink-0" />
            <span className="font-semibold text-slate-900 dark:text-white whitespace-nowrap">Fuente de Datos:</span>
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
                  {c.requires_permission_review && (
                    <span title="Pendiente de revisión de permisos">
                      <AlertTriangle className="w-3 h-3 text-amber-500 dark:text-amber-400 shrink-0" />
                    </span>
                  )}
                  {c.is_uploaded && (
                    <span title="Archivo importado">
                      <HardDrive className="w-3 h-3 text-cyan-600 dark:text-cyan-400 shrink-0" />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Aviso de default-deny pendiente: el caso accionable */}
      {needsReview && (
        <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-amber-800 dark:text-amber-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">
              «{selectedConnector?.name}» entró sin autorización: sus tablas están bloqueadas para todos los roles.
            </p>
            <p className="text-[11px] leading-relaxed">
              Se detectaron {selectedConnector?.detected_tables?.length ?? 0} tabla(s) y ninguna tiene permiso
              concedido. Mientras las casillas estén sin marcar, los usuarios de esos roles no ven estas tablas en el
              chat. Marca las que correspondan y guardá.
            </p>
          </div>
        </div>
      )}

      {rolesError && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{rolesError}</span>
        </div>
      )}

      {permissionsError && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{permissionsError}</span>
        </div>
      )}

      {saveError && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-400 text-xs flex items-start gap-2 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{saveError}</span>
        </div>
      )}

      {saveSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-800 dark:text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
          <Check className="w-4 h-4 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Matriz */}
      <div className="space-y-3">
        {isLoadingPermissions && (
          <p className="text-xs text-slate-500 dark:text-gray-400">Cargando permisos del servidor...</p>
        )}

        {!isLoadingPermissions && selectedConnectionId !== null && (
          <>
            {permissionsLoaded && !permissionsError && tables.length === 0 && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-dark-base/80 border border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 text-xs flex items-start gap-2">
                <Lock className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  El servidor no reportó ninguna tabla para esta fuente. Si esperabas ver tablas, recargá la fuente
                  desde «Fuentes BD Corporativas».
                </span>
              </div>
            )}

            {tables.length > 0 && (
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-dark-border">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-dark-base border-b border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3 whitespace-nowrap">Rol</th>
                      {tables.map((t) => (
                        <th
                          key={t}
                          className="px-3 py-3 text-center font-mono normal-case"
                          title={t}
                        >
                          <span className="block max-w-[120px] truncate">{t}</span>
                        </th>
                      ))}
                      <th className="px-3 py-3 text-right whitespace-nowrap">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-dark-border text-slate-800 dark:text-gray-200 bg-white dark:bg-transparent">
                    {roles.map((role) => (
                      <tr key={role.id} className="hover:bg-slate-50 dark:hover:bg-dark-card/50 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-white whitespace-nowrap">
                          {role.name}
                          {role.description && (
                            <p className="text-[10px] font-normal text-slate-500 dark:text-gray-500">
                              {role.description}
                            </p>
                          )}
                        </td>
                        {tables.map((t) => {
                          const checked = isChecked(role.id, t);
                          return (
                            <td key={t} className="px-3 py-3 text-center">
                              <input
                                type="checkbox"
                                aria-label={`Permiso de ${role.name} sobre ${t}`}
                                checked={checked}
                                disabled={isSaving}
                                onChange={() => toggleCell(role.id, t)}
                                className="w-4 h-4 text-brand-600 rounded border-slate-300 dark:border-dark-border dark:bg-dark-base focus:ring-brand-500 cursor-pointer"
                              />
                              {checked && grantedByAdmin(role.id, t) && (
                                <p className="text-[9px] text-emerald-600 dark:text-emerald-400 mt-0.5">
                                  por admin
                                </p>
                              )}
                            </td>
                          );
                        })}
                        <td className="px-3 py-3 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => grantAllToRole(role.id)}
                              disabled={isSaving}
                              className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-brand-50 text-brand-700 border border-brand-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/20 hover:bg-brand-100 dark:hover:bg-purple-500/20 transition-colors disabled:opacity-50 cursor-pointer"
                            >
                              Dar todas
                            </button>
                            <button
                              type="button"
                              onClick={() => revokeAllFromRole(role.id)}
                              disabled={isSaving}
                              className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-300 dark:bg-dark-card dark:text-gray-300 dark:border-dark-border hover:bg-slate-200 dark:hover:bg-dark-border transition-colors disabled:opacity-50 cursor-pointer"
                            >
                              Revocar todas
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {rolesLoaded && !rolesError && roles.length === 0 && !permissionsError && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-dark-base/80 border border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 text-xs">
                El servidor no devolvió ningún rol para esta matriz.
              </div>
            )}
          </>
        )}

        {/* Guardar: la única vía de granting */}
        <div className="flex items-center justify-end gap-3 pt-1">
          <span className="text-[11px] text-slate-500 dark:text-gray-400">
            {pendingCount === 0
              ? 'Sin cambios pendientes'
              : `${pendingCount} cambio(s) sin guardar`}
          </span>
          <button
            type="button"
            onClick={savePending}
            disabled={isSaving || pendingCount === 0}
            className="flex items-center space-x-1.5 text-xs bg-brand-600 hover:bg-brand-500 text-white font-medium px-4 py-2 rounded-xl shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
          >
            <Save className={`w-3.5 h-3.5 ${isSaving ? 'animate-pulse' : ''}`} />
            <span>{isSaving ? 'Guardando...' : 'Guardar Permisos'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};