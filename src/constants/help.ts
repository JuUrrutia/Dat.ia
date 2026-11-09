/**
 * Contenido estatico del Centro de Ayuda y del panel de atajos.
 *
 * Vive separado de las paginas para que el panel de atajos (montado en todas
 * las rutas protegidas) y la pagina /ayuda lean la MISMA lista: si se agrega
 * un atajo nuevo en `useChatEngine` o `ChatDashboardPage`, se documenta aqui
 * una sola vez.
 */

export interface KeyboardShortcut {
  keys: string[];
  description: string;
  scope: 'Global' | 'Chat' | 'Dashboard';
}

export const KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  { keys: ['?'], description: 'Abrir / cerrar este panel de atajos', scope: 'Global' },
  { keys: ['Esc'], description: 'Cerrar el modal o panel abierto', scope: 'Global' },
  { keys: ['Ctrl', 'N'], description: 'Iniciar una nueva conversación', scope: 'Chat' },
  { keys: ['Ctrl', 'K'], description: 'Buscar en el historial de conversaciones', scope: 'Chat' },
  { keys: ['Enter'], description: 'Enviar la pregunta', scope: 'Chat' },
  { keys: ['Shift', 'Enter'], description: 'Nueva línea dentro de la pregunta', scope: 'Chat' },
  { keys: ['F11'], description: 'Activar / salir del modo presentación', scope: 'Dashboard' },
];

export interface FaqItem {
  question: string;
  answer: string;
  category: 'Uso' | 'Seguridad' | 'Datos' | 'Cuenta';
}

export const FAQ_ITEMS: FaqItem[] = [
  {
    category: 'Uso',
    question: '¿Necesito saber SQL para usar Dat.ia?',
    answer:
      'No. Escribes tu pregunta en español, como se la harías a un colega ("¿Cuáles fueron las ventas por región el último trimestre?"). La IA genera la consulta SQL, la valida y te devuelve tablas, gráficos e indicadores.',
  },
  {
    category: 'Uso',
    question: '¿Cómo obtengo mejores respuestas?',
    answer:
      'Sé específico: indica el período ("en 2025", "último mes"), la métrica ("monto total", "promedio") y el corte ("por región", "por producto"). Si la respuesta no es la esperada, reformula agregando el nombre de la tabla o columna que te interesa.',
  },
  {
    category: 'Uso',
    question: '¿Puedo exportar los resultados?',
    answer:
      'Sí. Cada respuesta con datos permite copiar la tabla (compatible con Excel y Google Sheets) y los informes ejecutivos se pueden exportar a PDF o Excel desde la barra de exportación del informe.',
  },
  {
    category: 'Uso',
    question: '¿Qué es el modo presentación?',
    answer:
      'Presiona F11 dentro del Dashboard para ocultar la barra lateral y mostrar los gráficos a pantalla completa, ideal para reuniones. Presiona Esc o F11 nuevamente para salir.',
  },
  {
    category: 'Seguridad',
    question: '¿Mis datos salen de la empresa?',
    answer:
      'No. El modelo de lenguaje se ejecuta de forma local (llama.cpp u Ollama). Ninguna pregunta ni resultado se envía a servicios en la nube.',
  },
  {
    category: 'Seguridad',
    question: '¿La IA puede modificar o borrar datos?',
    answer:
      'No. Toda consulta pasa por el AST Guardrail, que analiza el SQL generado y solo permite una sentencia SELECT de lectura. Comandos como DROP, DELETE, UPDATE o INSERT se bloquean antes de llegar a la base de datos.',
  },
  {
    category: 'Seguridad',
    question: '¿Por qué algunas columnas aparecen enmascaradas o no puedo consultar una tabla?',
    answer:
      'Tu perfil (rol) define qué tablas y columnas puedes ver. Los datos sensibles —RUTs, cuentas bancarias, tokens— se enmascaran o bloquean según la matriz RBAC. Si necesitas acceso, solicítalo a un administrador de la plataforma.',
  },
  {
    category: 'Seguridad',
    question: '¿Quedan registradas mis consultas?',
    answer:
      'Sí. Por cumplimiento, cada consulta queda en la bitácora de auditoría con la pregunta, el SQL ejecutado, el resultado de la validación y el tiempo de respuesta. Solo los administradores pueden revisarla.',
  },
  {
    category: 'Datos',
    question: '¿Qué tan confiables son las predicciones?',
    answer:
      'Las proyecciones se calculan sobre los datos históricos disponibles y muestran su nivel de confianza. Úsalas como apoyo a la decisión, no como certeza: con pocos datos o series muy irregulares la incertidumbre es mayor.',
  },
  {
    category: 'Datos',
    question: '¿Cómo verifico de dónde sale una cifra?',
    answer:
      'Abre la trazabilidad de la respuesta: verás el SQL exacto que se ejecutó, la base de datos consultada y las filas devueltas. Puedes copiar ese SQL y ejecutarlo tú mismo para comprobarlo.',
  },
  {
    category: 'Cuenta',
    question: '¿Cómo cambio mi contraseña?',
    answer:
      'Pide a un administrador que la restablezca desde Gobernanza RBAC. Al entrar con la clave temporal, el sistema te pedirá crear una nueva y se cerrarán tus otras sesiones abiertas.',
  },
  {
    category: 'Cuenta',
    question: 'Mi cuenta quedó bloqueada, ¿qué hago?',
    answer:
      'Tras varios intentos fallidos la cuenta se bloquea temporalmente. Espera unos minutos o pide a un administrador que restablezca tu contraseña desde Gobernanza RBAC.',
  },
];

export interface GlossaryTerm {
  term: string;
  definition: string;
}

export const GLOSSARY: GlossaryTerm[] = [
  { term: 'Text-to-SQL', definition: 'Traducción automática de una pregunta en lenguaje natural a una consulta SQL.' },
  { term: 'LLM local', definition: 'Modelo de lenguaje que corre en servidores propios, sin conexión a internet.' },
  { term: 'RBAC', definition: 'Control de acceso basado en roles: tu perfil determina qué datos puedes consultar.' },
  { term: 'CLS', definition: 'Column-Level Security: protección a nivel de columna que enmascara datos sensibles.' },
  { term: 'AST Guardrail', definition: 'Validador que analiza la estructura del SQL y bloquea todo lo que no sea lectura.' },
  { term: 'KPI', definition: 'Indicador clave de desempeño, como ventas totales o margen promedio.' },
  { term: 'Trazabilidad', definition: 'Registro del SQL, la fuente y el resultado detrás de cada respuesta.' },
  { term: 'Catálogo semántico', definition: 'Descripción de tablas y columnas en términos de negocio que ayuda a la IA a entender tus datos.' },
];

export interface QuickStartStep {
  title: string;
  description: string;
}

export const QUICK_START_STEPS: QuickStartStep[] = [
  {
    title: 'Haz tu pregunta',
    description: 'Escribe en el chat lo que quieres saber, en español y con tus palabras.',
  },
  {
    title: 'Revisa el resultado',
    description: 'Dat.ia muestra KPIs, gráficos interactivos y la tabla de datos que respalda la respuesta.',
  },
  {
    title: 'Profundiza',
    description: 'Cambia el tipo de gráfico, pide un informe ejecutivo o una proyección sobre los mismos datos.',
  },
  {
    title: 'Verifica y comparte',
    description: 'Consulta la trazabilidad (SQL ejecutado) y exporta a PDF o Excel para compartir.',
  },
];

export const EXAMPLE_QUESTIONS: { category: string; questions: string[] }[] = [
  {
    category: 'Finanzas & Comercial',
    questions: [
      '¿Cuál fue el total de ventas por mes en el último año?',
      '¿Qué 10 productos tienen mayor margen?',
    ],
  },
  {
    category: 'Talento & Operaciones',
    questions: [
      '¿Cuántos colaboradores hay por área?',
      '¿Cómo evolucionó el índice de clima laboral por trimestre?',
    ],
  },
  {
    category: 'Datos & BI',
    questions: [
      '¿Existe relación entre descuento aplicado y volumen vendido?',
      'Proyecta las ventas de los próximos 3 meses',
    ],
  },
];
