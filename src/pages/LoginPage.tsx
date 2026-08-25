import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, ShieldCheck, Database, Lock, KeyRound, Mail, UserPlus, LogIn, ArrowRight, AlertCircle } from 'lucide-react';
import logoDatia2 from './Logo_datia_2.png';

const PRESET_USERS = [
  { name: 'Administrador', username: 'admin', password: 'admin123', role: 'Administrador', is_admin: true },
  { name: 'Economista', username: 'economista', password: 'economista123', role: 'Economista', is_admin: false },
  { name: 'Soporte TI', username: 'ti', password: 'ti123', role: 'TI', is_admin: false },
];

export const LoginPage: React.FC = () => {
  const { login, register, loginDemo, error, clearError } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');

  // Form Fields
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

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

  const handlePresetLogin = async (u: typeof PRESET_USERS[0]) => {
    setUsername(u.username);
    setPassword(u.password);
    setLocalError(null);
    clearError();
    setIsSubmitting(true);
    try {
      await login(u.username, u.password);
    } catch (err: any) {
      loginDemo(u.username, u.role, u.is_admin);
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeError = localError || error;

  return (
    <div className="min-h-screen bg-dark-base flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow Accents */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-dark-card/60 shadow-xl shadow-brand-600/20 mb-2 overflow-hidden border border-brand-500/20">
            <img src={logoDatia2} alt="Logo Datia" className="w-full h-full object-contain p-1" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Dat.ia</h1>
          <p className="text-xs text-gray-400">Transformando datos en decisiones</p>
        </div>

        {/* Card Panel */}
        <div className="glass-panel rounded-3xl p-7 border border-white/10 shadow-2xl space-y-6">
          {/* Mode Switcher Tabs */}
          <div className="flex bg-dark-base/80 p-1 rounded-xl border border-dark-border">
            <button
              type="button"
              onClick={() => { setMode('login'); setLocalError(null); clearError(); }}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-semibold transition-colors ${
                mode === 'login'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'text-gray-400 hover:text-white'
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
                  : 'text-gray-400 hover:text-white'
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
                  className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
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
                    className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
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
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                />
                <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              </div>
            </div>

            {mode === 'register' && (
              <div className="space-y-1.5 animate-fadeIn">
                <label htmlFor="login-confirm-password-input" className="block text-xs font-semibold text-gray-300">Confirmar Contraseña</label>
                <div className="relative">
                  <input
                    id="login-confirm-password-input"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
                  />
                  <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex items-center justify-center space-x-2 bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 text-white font-semibold py-2.5 rounded-xl shadow-lg shadow-brand-600/30 transition-colors disabled:opacity-50"
            >
              <span>{isSubmitting ? 'Procesando...' : mode === 'login' ? 'Acceder al Sistema' : 'Crear Cuenta'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Selector for 3 Profiles */}
          <div className="pt-4 border-t border-dark-border/60">
            <p className="text-[11px] text-gray-400 text-center mb-2.5">O prueba directamente con un perfil asignado:</p>
            <div className="grid grid-cols-3 gap-2">
              {PRESET_USERS.map((u) => (
                <button
                  key={u.username}
                  type="button"
                  onClick={() => handlePresetLogin(u)}
                  className="bg-dark-base/50 hover:bg-dark-card border border-dark-border hover:border-brand-500/40 rounded-lg p-2 text-center transition-colors"
                >
                  <div className="text-[11px] font-semibold text-gray-200 truncate">{u.name}</div>
                  <div className="text-[9px] text-brand-400 truncate">{u.role}</div>
                </button>
              ))}
            </div>
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
