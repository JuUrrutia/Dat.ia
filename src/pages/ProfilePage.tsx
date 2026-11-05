import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserCircle,
  Mail,
  ShieldCheck,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  LifeBuoy,
  LogOut,
  Crown,
  Info,
} from 'lucide-react';
import { useAuth } from '../features/auth/context/AuthContext';
import { authService } from '../features/auth/services/auth_service';
import { useNotifications } from '../context/NotificationContext';
import { CORPORATE_ROLES, getRoleBadgeStyle } from '../constants';

/** Debe coincidir con MIN_PASSWORD_LENGTH en backend/app/modules/auth/schemas.py */
const MIN_PASSWORD_LENGTH = 6;

interface StrengthResult {
  score: 0 | 1 | 2 | 3 | 4;
  label: string;
  color: string;
}

/**
 * Indicador orientativo. La unica regla obligatoria es el largo minimo que
 * valida el backend; el resto solo ayuda al usuario a elegir mejor.
 */
const evaluateStrength = (pwd: string): StrengthResult => {
  if (!pwd) return { score: 0, label: '', color: 'bg-slate-300 dark:bg-dark-border' };
  let score = 0;
  if (pwd.length >= MIN_PASSWORD_LENGTH) score++;
  if (pwd.length >= 10) score++;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
  if (/\d/.test(pwd) && /[^A-Za-z0-9]/.test(pwd)) score++;
  if (pwd.length < MIN_PASSWORD_LENGTH) score = 0;
  const table: StrengthResult[] = [
    { score: 0, label: 'Muy débil', color: 'bg-rose-500' },
    { score: 1, label: 'Débil', color: 'bg-orange-500' },
    { score: 2, label: 'Aceptable', color: 'bg-amber-500' },
    { score: 3, label: 'Buena', color: 'bg-lime-500' },
    { score: 4, label: 'Excelente', color: 'bg-emerald-500' },
  ];
  return table[score];
};

const getInitials = (name: string) =>
  name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('') || '?';

const inputClass =
  'w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-white dark:bg-dark-base border border-slate-200 dark:border-dark-border text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/50';

export const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { notify } = useNotifications();
  const navigate = useNavigate();

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const strength = useMemo(() => evaluateStrength(newPassword), [newPassword]);

  if (!user) return null;

  const roleName = user.role_name || (user.is_admin ? 'Super Administrador' : 'Usuario');
  const roleDef = CORPORATE_ROLES.find((r) => r.name === roleName);

  const checks = [
    { ok: newPassword.length >= MIN_PASSWORD_LENGTH, text: `Al menos ${MIN_PASSWORD_LENGTH} caracteres` },
    { ok: !!newPassword && newPassword === confirmPassword, text: 'Ambas contraseñas coinciden' },
    { ok: !!newPassword && newPassword !== oldPassword, text: 'Distinta a la contraseña actual' },
  ];
  const canSubmit = !!oldPassword && checks.every((c) => c.ok) && !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    if (!canSubmit) return;

    setLoading(true);
    try {
      const res = (await authService.changePassword(oldPassword, newPassword)) as {
        message: string;
        revoked_sessions?: number;
      };
      const revoked = res.revoked_sessions ?? 0;
      const msg =
        revoked > 0
          ? `Contraseña actualizada. Se cerraron ${revoked} sesión(es) abiertas en otros dispositivos.`
          : 'Contraseña actualizada correctamente.';
      setSuccessMsg(msg);
      notify('success', msg);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'No se pudo actualizar la contraseña. Verifica tu clave actual.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full flex-1 bg-dark-base overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar pb-28 font-sans">
      {/* Tarjeta de identidad */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/10 shadow-2xl flex flex-col sm:flex-row sm:items-center gap-5">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-2xl sm:text-3xl font-extrabold shadow-lg shrink-0">
          {getInitials(user.username)}
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900 dark:text-white tracking-tight truncate">
              {user.username}
            </h1>
            {user.is_admin && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/30">
                <Crown className="w-3 h-3" /> Admin
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5" />
              {user.email || 'Sin correo registrado'}
            </span>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-semibold ${getRoleBadgeStyle(roleName)}`}>
              <ShieldCheck className="w-3.5 h-3.5" />
              {roleDef?.label || roleName}
            </span>
          </div>
        </div>
        <div className="flex sm:flex-col gap-2 shrink-0">
          <button
            type="button"
            onClick={() => navigate('/ayuda')}
            className="flex-1 flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border border-slate-200 dark:border-dark-border text-slate-700 dark:text-gray-300 hover:border-brand-500/40 transition-colors"
          >
            <LifeBuoy className="w-4 h-4" /> Ayuda
          </button>
          <button
            type="button"
            onClick={logout}
            className="flex-1 flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Cerrar sesión
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Rol y permisos */}
        <section aria-labelledby="role-title" className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
          <h2 id="role-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-500" /> Tu rol y accesos
          </h2>
          <div className="rounded-xl border border-slate-200 dark:border-dark-border/70 bg-white/60 dark:bg-dark-base/50 p-4 space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
              {roleDef?.category ? `Categoría · ${roleDef.category}` : 'Perfil'}
            </div>
            <div className="text-sm font-semibold text-gray-900 dark:text-white">{roleDef?.label || roleName}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              {roleDef?.description ||
                (user.is_admin
                  ? 'Acceso completo a la plataforma, incluida la gobernanza RBAC.'
                  : 'Perfil con acceso a las tablas que el administrador haya habilitado.')}
            </p>
          </div>

          <ul className="space-y-2 text-xs">
            <li className="flex items-start gap-2 text-slate-600 dark:text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-px" />
              Consultas de solo lectura validadas por AST Guardrail.
            </li>
            <li className="flex items-start gap-2 text-slate-600 dark:text-gray-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-px" />
              Columnas sensibles enmascaradas según tu rol (CLS).
            </li>
            <li className="flex items-start gap-2 text-slate-600 dark:text-gray-300">
              {user.is_admin ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-px" />
              ) : (
                <Info className="w-4 h-4 text-gray-400 shrink-0 mt-px" />
              )}
              {user.is_admin
                ? 'Puedes gestionar usuarios, permisos, conexiones y auditoría.'
                : 'La gestión de usuarios y permisos está reservada a administradores.'}
            </li>
          </ul>

          {!user.is_admin && (
            <p className="text-[11px] text-gray-400 leading-relaxed border-t border-slate-200 dark:border-dark-border pt-3">
              ¿Necesitas consultar otra tabla? Solicita el acceso al administrador de la plataforma indicando tu usuario
              <span className="font-mono text-gray-500 dark:text-gray-300"> {user.username}</span>.
            </p>
          )}
        </section>

        {/* Cambio de contraseña */}
        <section aria-labelledby="password-title" className="lg:col-span-3 glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 id="password-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-brand-500" /> Cambiar contraseña
            </h2>
            <button
              type="button"
              onClick={() => setShowPasswords((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
              aria-pressed={showPasswords}
            >
              {showPasswords ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {showPasswords ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
            <div className="space-y-1.5">
              <label htmlFor="profile-old-pwd" className="text-xs font-semibold text-slate-700 dark:text-gray-300">
                Contraseña actual
              </label>
              <input
                id="profile-old-pwd"
                type={showPasswords ? 'text' : 'password'}
                autoComplete="current-password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className={inputClass}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div className="space-y-1.5">
                <label htmlFor="profile-new-pwd" className="text-xs font-semibold text-slate-700 dark:text-gray-300">
                  Nueva contraseña
                </label>
                <input
                  id="profile-new-pwd"
                  type={showPasswords ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="profile-confirm-pwd" className="text-xs font-semibold text-slate-700 dark:text-gray-300">
                  Confirmar nueva contraseña
                </label>
                <input
                  id="profile-confirm-pwd"
                  type={showPasswords ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            {/* Medidor de robustez */}
            {newPassword && (
              <div className="space-y-1.5" aria-live="polite">
                <div className="flex gap-1">
                  {[1, 2, 3, 4].map((n) => (
                    <div
                      key={n}
                      className={`h-1.5 flex-1 rounded-full transition-colors ${
                        strength.score >= n ? strength.color : 'bg-slate-200 dark:bg-dark-border'
                      }`}
                    />
                  ))}
                </div>
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  Robustez: <span className="font-semibold">{strength.label}</span>
                  {strength.score < 3 && ' · combina mayúsculas, números y símbolos para mejorarla.'}
                </div>
              </div>
            )}

            <ul className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
              {checks.map((c) => (
                <li
                  key={c.text}
                  className={`flex items-center gap-1.5 text-[11px] ${c.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400'}`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  {c.text}
                </li>
              ))}
            </ul>

            {error && (
              <div role="alert" className="flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-xl px-3 py-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
                {error}
              </div>
            )}
            {successMsg && (
              <div role="status" className="flex items-start gap-2 text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-3 py-2.5">
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-px" />
                {successMsg}
              </div>
            )}

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
              <p className="text-[11px] text-gray-400">
                Por seguridad, al cambiarla se cerrarán tus sesiones en otros dispositivos.
              </p>
              <button
                type="submit"
                disabled={!canSubmit}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-brand-600 text-white hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm shrink-0"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                {loading ? 'Actualizando…' : 'Actualizar contraseña'}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div className="flex items-center gap-2 text-[11px] text-gray-400 justify-center">
        <UserCircle className="w-3.5 h-3.5" />
        ID de usuario #{user.id}
      </div>
    </div>
  );
};
