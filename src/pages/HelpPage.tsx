import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LifeBuoy,
  Search,
  MessageSquareText,
  BarChart3,
  Layers,
  ShieldCheck,
  ChevronDown,
  Keyboard,
  BookOpen,
  Lock,
  Cpu,
  FileCheck2,
  Sparkles,
  ArrowRight,
  UserCircle,
} from 'lucide-react';
import {
  FAQ_ITEMS,
  FaqItem,
  GLOSSARY,
  KEYBOARD_SHORTCUTS,
  QUICK_START_STEPS,
  EXAMPLE_QUESTIONS,
} from '../constants/help';
import { ShortcutKeys, openKeyboardShortcuts } from '../components/shared/KeyboardShortcutsModal';
import { copyToClipboard } from '../shared/clipboard';
import { useNotifications } from '../context/NotificationContext';

const STEP_ICONS = [MessageSquareText, BarChart3, Layers, FileCheck2];

const SECURITY_LAYERS = [
  {
    icon: Lock,
    title: 'Matriz RBAC',
    description: 'Tu rol define qué tablas puedes consultar. Lo que no está permitido, la IA ni siquiera lo ve.',
  },
  {
    icon: ShieldCheck,
    title: 'Guard de dominio',
    description: 'Las preguntas fuera del ámbito de los datos corporativos se detectan y no se ejecutan.',
  },
  {
    icon: Cpu,
    title: 'IA 100% local',
    description: 'El modelo corre en servidores propios. Ningún dato sale de la organización.',
  },
  {
    icon: FileCheck2,
    title: 'AST Guardrail',
    description: 'El SQL generado se analiza y solo se permite una sentencia SELECT de lectura.',
  },
];

const FAQ_CATEGORIES: Array<FaqItem['category'] | 'Todas'> = ['Todas', 'Uso', 'Seguridad', 'Datos', 'Cuenta'];

/** Normaliza para buscar sin importar tildes ni mayusculas. */
const normalize = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export const HelpPage: React.FC = () => {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<(typeof FAQ_CATEGORIES)[number]>('Todas');
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const filteredFaq = useMemo(() => {
    const q = normalize(query.trim());
    return FAQ_ITEMS.filter((item) => {
      if (category !== 'Todas' && item.category !== category) return false;
      if (!q) return true;
      return normalize(item.question).includes(q) || normalize(item.answer).includes(q);
    });
  }, [query, category]);

  const filteredGlossary = useMemo(() => {
    const q = normalize(query.trim());
    if (!q) return GLOSSARY;
    return GLOSSARY.filter((g) => normalize(g.term).includes(q) || normalize(g.definition).includes(q));
  }, [query]);

  const handleCopyExample = async (text: string) => {
    const ok = await copyToClipboard(text);
    notify(ok ? 'success' : 'error', ok ? 'Pregunta copiada. Pégala en el chat.' : 'No se pudo copiar la pregunta.');
  };

  return (
    <div className="w-full h-full flex-1 bg-dark-base overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar pb-28 font-sans">
      {/* Banner */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-white/10 shadow-2xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-11 h-11 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-sm shrink-0">
              <LifeBuoy className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-extrabold text-gray-900 dark:text-white tracking-tight">
                Centro de Ayuda
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Guía rápida, preguntas frecuentes y todo lo que necesitas para sacar provecho a Datia.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={openKeyboardShortcuts}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border border-slate-200 dark:border-dark-border bg-slate-100 dark:bg-dark-base/70 text-slate-700 dark:text-gray-300 hover:border-brand-500/40 transition-colors"
            >
              <Keyboard className="w-4 h-4" />
              Atajos <span className="hidden sm:inline text-gray-400">(?)</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white hover:bg-brand-500 transition-colors shadow-sm"
            >
              Ir al chat
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        <label className="relative block">
          <span className="sr-only">Buscar en la ayuda</span>
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Busca en preguntas frecuentes y glosario… (ej. contraseña, exportar, RBAC)"
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-white dark:bg-dark-base border border-slate-200 dark:border-dark-border text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
          />
        </label>
      </div>

      {/* Guia rapida */}
      {!query && (
        <section aria-labelledby="quickstart-title" className="space-y-3">
          <h2 id="quickstart-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-500" /> Primeros pasos
          </h2>
          <ol className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {QUICK_START_STEPS.map((step, i) => {
              const Icon = STEP_ICONS[i % STEP_ICONS.length];
              return (
                <li key={step.title} className="glass-card p-4 rounded-2xl border border-white/10 space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-600 dark:text-brand-300 text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <Icon className="w-4 h-4 text-gray-400" />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{step.title}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{step.description}</p>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* FAQ */}
        <section aria-labelledby="faq-title" className="xl:col-span-2 glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 id="faq-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <MessageSquareText className="w-4 h-4 text-brand-500" /> Preguntas frecuentes
            </h2>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filtrar por categoría">
              {FAQ_CATEGORIES.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-pressed={category === c}
                  onClick={() => {
                    setCategory(c);
                    setOpenIndex(null);
                  }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-colors ${
                    category === c
                      ? 'bg-brand-600 text-white border-brand-600'
                      : 'border-slate-200 dark:border-dark-border text-slate-600 dark:text-gray-400 hover:border-brand-500/40'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {filteredFaq.length === 0 ? (
            <p className="text-xs text-gray-400 py-6 text-center">
              No encontramos preguntas para "{query}". Prueba con otra palabra o consulta a tu administrador.
            </p>
          ) : (
            <ul className="space-y-2">
              {filteredFaq.map((item, i) => {
                const isOpen = openIndex === i || (!!query && filteredFaq.length <= 3);
                const panelId = `faq-panel-${i}`;
                return (
                  <li key={item.question} className="rounded-xl border border-slate-200 dark:border-dark-border/70 bg-white/60 dark:bg-dark-base/50 overflow-hidden">
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-controls={panelId}
                      onClick={() => setOpenIndex(isOpen ? null : i)}
                      className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left"
                    >
                      <span className="flex items-center gap-2.5 min-w-0">
                        <span className="text-[10px] font-bold uppercase tracking-wide text-brand-600 dark:text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded-md shrink-0">
                          {item.category}
                        </span>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{item.question}</span>
                      </span>
                      <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {isOpen && (
                      <div id={panelId} className="px-4 pb-4 text-xs text-slate-600 dark:text-gray-300 leading-relaxed">
                        {item.answer}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Columna derecha: atajos + glosario */}
        <div className="space-y-6">
          <section aria-labelledby="shortcuts-title" className="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
            <h2 id="shortcuts-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Keyboard className="w-4 h-4 text-brand-500" /> Atajos de teclado
            </h2>
            <ul className="space-y-1.5">
              {KEYBOARD_SHORTCUTS.map((s) => (
                <li key={s.description} className="flex items-center justify-between gap-3 text-xs text-slate-600 dark:text-gray-300">
                  <span>{s.description}</span>
                  <ShortcutKeys shortcut={s} />
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="glossary-title" className="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
            <h2 id="glossary-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-brand-500" /> Glosario
            </h2>
            {filteredGlossary.length === 0 ? (
              <p className="text-xs text-gray-400">Sin términos que coincidan.</p>
            ) : (
              <dl className="space-y-2.5">
                {filteredGlossary.map((g) => (
                  <div key={g.term}>
                    <dt className="text-xs font-semibold text-gray-900 dark:text-white">{g.term}</dt>
                    <dd className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{g.definition}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        </div>
      </div>

      {!query && (
        <>
          {/* Ejemplos */}
          <section aria-labelledby="examples-title" className="glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
            <div>
              <h2 id="examples-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-500" /> Ideas de preguntas
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Haz clic para copiar. Las respuestas dependen de las tablas que tu rol tenga habilitadas.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {EXAMPLE_QUESTIONS.map((group) => (
                <div key={group.category} className="space-y-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{group.category}</div>
                  {group.questions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleCopyExample(q)}
                      className="w-full text-left text-xs px-3 py-2.5 rounded-xl border border-slate-200 dark:border-dark-border bg-white/60 dark:bg-dark-base/50 text-slate-700 dark:text-gray-300 hover:border-brand-500/40 hover:text-gray-900 dark:hover:text-white transition-colors"
                    >
                      “{q}”
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </section>

          {/* Seguridad */}
          <section aria-labelledby="security-title" className="space-y-3">
            <h2 id="security-title" className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500" /> Cómo protegemos tus datos
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
              {SECURITY_LAYERS.map(({ icon: Icon, title, description }) => (
                <div key={title} className="glass-card p-4 rounded-2xl border border-white/10 space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Contacto */}
          <div className="glass-panel p-5 rounded-2xl border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">¿Necesitas más acceso o algo no funciona?</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Los permisos sobre tablas y columnas los gestiona el administrador de la plataforma. Revisa tu perfil para ver tu rol actual.
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/perfil')}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border border-brand-500/40 text-brand-700 dark:text-brand-300 hover:bg-brand-500/10 transition-colors shrink-0"
            >
              <UserCircle className="w-4 h-4" />
              Ver mi perfil
            </button>
          </div>
        </>
      )}
    </div>
  );
};
