import React, { useState } from 'react';
import { useAuth } from '../features/auth/context/AuthContext';
import { ShieldCheck, Database, Lock, KeyRound, Mail, UserPlus, LogIn, ArrowRight, AlertCircle, Eye, EyeOff, Users, ChevronDown } from 'lucide-react';
import { CORPORATE_ROLES } from '../constants';
import logoDatiaDark from './Logo_datia_2.png';
import logoDatiaLight from './Logo_Datia_3.png';

// Las credenciales de la demo viven aca porque el backend las siembra; el NOMBRE
// del rol sale de `CORPORATE_ROLES`, que es la unica lista del frontend. Escribir
// el nombre dos veces hacia que el perfil del desplegable y el badge del Header
// digan cosas distintas en cuanto uno de los dos se toca.
//
// El orden sigue el de la matriz de `init_db`, de mas a menos privilegios.
const DEMO_PASSWORDS: Record<string, string> = {
  'Administrador de Plataforma': 'admin123',
  'Director Ejecutivo (C-Level)': 'director123',
  'Analista Financiero & Comercial': 'economista123',
  'Gerente de Talento & Operaciones': 'talento123',
  'Analista de Datos & BI': 'bi123',
  'Ingeniero de Infraestructura & TI': 'ti123',
  'Oficial de Cumplimiento & Seguridad': 'seguridad123',
  'Usuario Consultor': 'consultor123',
};

const DEMO_USERNAMES: Record<string, string> = {
  'Administrador de Plataforma': 'admin',
  'Director Ejecutivo (C-Level)': 'director',
  'Analista Financiero & Comercial': 'economista',
  'Gerente de Talento & Operaciones': 'talento',
  'Analista de Datos & BI': 'bi',
  'Ingeniero de Infraestructura & TI': 'ti',
  'Oficial de Cumplimiento & Seguridad': 'seguridad',
  'Usuario Consultor': 'consultor',
};

const DEMO_PROFILES = CORPORATE_ROLES
  .filter((r) => DEMO_USERNAMES[r.name])
  .map((r) => ({
    role: r.name,
    username: DEMO_USERNAMES[r.name],
    password: DEMO_PASSWORDS[r.name],
  }));

const PERFIL_INICIAL = DEMO_PROFILES[0].username;

export const LoginPage: React.FC = () => {
  const { login, register, error, clearError } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');

  // Form Fields
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  // Perfil elegido en el desplegable de la demo. Es estado propio, no el valor de
  // `username`: el desplegable elige una cuenta y el login manual escribe en el
  // campo. Si compartieran estado, teclear un usuario cerrando en el perfil
  // "Administrador" pondria las credenciales de otro sin que nadie lo pidiera.
  const [perfilDemo, setPerfilDemo] = useState<string>(PERFIL_INICIAL);
  // One toggle for both password fields on purpose: confirming a password means
  // comparing the two, which needs them visible at the same time.
  const [showPasswords, setShowPasswords] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!username.trim() || !password) {
      setLocalError('Por favor completa todos los campos requeridos.');
      return;
    }

    if (mode === 'register') {
      if (password !== confirmPassword) {
        setLocalError('Las contraseñas no coinciden.');
        return;
      }
      if (password.length < 6) {
        setLocalError('La contraseña debe tener al menos 6 caracteres.');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login(username, password);
      } else {
        await register(username, email, password);
      }
    } catch (err: any) {
      setLocalError(err.message || 'Credenciales inválidas. Verifica tu usuario y contraseña.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Elegir un perfil RELLENA el formulario en vez de entrar directo. El login
  // manual queda por encima y es el que manda; con autologin, cambiar el
  // desplegable se comia la sesion de alguien que solo estaba mirando el
  // catalogo de roles. Rellenar deja la accion a un click explicito y hace
  // visible que esas credenciales son de la demo y no un atajo.
  const handlePerfilChange = (username: string) => {
    setPerfilDemo(username);
    const p = DEMO_PROFILES.find((x) => x.username === username);
    if (!p) return;
    setUsername(p.username);
    setPassword(p.password);
    setLocalError(null);
    clearError();
  };
  const activeError = localError || error;

  return (
    <div className="min-h-[100dvh] bg-dark-base flex items-center justify-center p-4 relative overflow-hidden">
      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-dark-card/60 shadow-md mb-2 overflow-hidden border border-white/10">
            <img src={logoDatiaLight} alt="Logo de Dat.ia" className="block dark:hidden w-full h-full object-contain p-1" />
            <img src={logoDatiaDark} alt="Logo de Dat.ia" className="hidden dark:block w-full h-full object-contain p-1" />
          </div>
          <h1 className="text-2xl font-extrabold text-app-text tracking-tight">Dat.ia</h1>
          <p className="text-xs text-gray-400">Transformando datos en decisiones</p>
        </div>

        {/* Card Panel */}
        <div className="glass-panel rounded-2xl p-7 border border-white/10 shadow-xl space-y-6">
          {/* Mode Switcher Tabs */}
          <div className="flex bg-dark-base/80 p-1 rounded-xl border border-dark-border">
            <button
              type="button"
              onClick={() => { setMode('login'); setLocalError(null); clearError(); }}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-semibold transition-colors ${
                mode === 'login'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-gray-400 hover:text-app-text'
              }`}
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Iniciar Sesión</span>
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setLocalError(null); clearError(); }}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-semibold transition-colors ${
                mode === 'register'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-gray-400 hover:text-app-text'
              }`}
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Registrarse</span>
            </button>
          </div>

          {/* Alert Message */}
          {activeError && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start space-x-2.5 animate-fadeIn">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{activeError}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="login-username-input" className="block text-xs font-semibold text-gray-300">Usuario Corporativo</label>
              <div className="relative">
                <input
                  id="login-username-input"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ej. economista"
                  required
                  className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-app-text placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                />
                <KeyRound className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              </div>
            </div>

            {mode === 'register' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label htmlFor="login-email-input" className="block text-xs font-semibold text-gray-300">Correo Electrónico</label>
                <div className="relative">
                  <input
                    id="login-email-input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="usuario@empresa.com"
                    required
                    className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-app-text placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                  />
                  <Mail className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="login-password-input" className="block text-xs font-semibold text-gray-300">Contraseña</label>
              <div className="relative">
                <input
                  id="login-password-input"
                  name="password"
                  type={showPasswords ? 'text' : 'password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-10 py-2.5 text-xs text-app-text placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                />
                <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                <button
                  type="button"
                  onClick={() => setShowPasswords((v) => !v)}
                  aria-label={showPasswords ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-gray-400 hover:text-app-text hover:bg-dark-card transition-colors"
                >
                  {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {mode === 'register' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label htmlFor="login-confirm-password-input" className="block text-xs font-semibold text-gray-300">Confirmar Contraseña</label>
                <div className="relative">
                  <input
                    id="login-confirm-password-input"
                    name="confirmPassword"
                    type={showPasswords ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-10 py-2.5 text-xs text-app-text placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                  />
                  <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex items-center justify-center space-x-2 bg-brand-600 hover:bg-brand-500 active:scale-[0.99] text-white font-semibold py-2.5 rounded-xl shadow-md shadow-brand-600/25 transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{isSubmitting ? 'Procesando...' : mode === 'login' ? 'Acceder al Sistema' : 'Crear Cuenta'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Selector de perfil de la demo: un desplegable y no una fila de
              botones. Los 8 perfiles no entran en tres botones sin que las
              etiquetas se corten, y un desplegable deja leer el nombre completo
              del rol, que es justo lo que hay que comparar entre perfiles. */}
          <div className="pt-4 border-t border-dark-border/60">
            <label
              htmlFor="login-demo-perfil"
              className="block text-[11px] text-gray-400 mb-2 font-medium"
            >
              O entra con un perfil de la demo
            </label>
            <div className="relative">
              <select
                id="login-demo-perfil"
                value={perfilDemo}
                onChange={(e) => handlePerfilChange(e.target.value)}
                className="w-full appearance-none bg-dark-base/50 border border-dark-border hover:border-brand-500/40 focus:outline-none focus:border-brand-500 rounded-xl pl-9 pr-9 py-2.5 text-xs text-app-text transition-colors cursor-pointer"
              >
                {DEMO_PROFILES.map((p) => (
                  <option key={p.username} value={p.username} className="bg-dark-card text-app-text">
                    {p.role} — {p.username}
                  </option>
                ))}
              </select>
              <Users className="w-4 h-4 text-gray-500 absolute left-3 top-3 pointer-events-none" />
              <ChevronDown className="w-4 h-4 text-gray-500 absolute right-3 top-3 pointer-events-none" />
            </div>
            <p className="text-[10px] text-gray-500 mt-1.5 text-center">
              Rellena el formulario. El acceso ocurre al pulsar «Acceder al Sistema».
            </p>
          </div>
        </div>

        {/* Footer Badges */}
        <div className="mt-5 flex items-center justify-center space-x-6 text-xs text-gray-400">
          <div className="flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>PostgreSQL Encriptado</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Database className="w-4 h-4 text-brand-400" />
            <span>Hashing Argon2/bcrypt</span>
          </div>
        </div>
      </div>
    </div>
  );
};
