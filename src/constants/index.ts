/**
 * Centralized Application Constants for Frontend
 */

export const DEFAULT_LLM_PROVIDER = 'llama_cpp';
export const DEFAULT_OLLAMA_URL = 'http://127.0.0.1:8080';
export const DEFAULT_LLM_MODEL = 'qwen2.5-coder:7b';

/**
 * Defaults por proveedor LLM: URL y modelo que se ofrecen al cambiar de
 * proveedor en el panel de ajustes.
 *
 * Esta tabla es la UNICA lista de endpoints LLM locales del frontend. Antes
 * estaba triplicada (aqui, en `useSettingsDiagnostics` y en `llm_service`) y cada
 * copia se podia desincronizar. El diagnostico la recorre para probar cada
 * servidor via backend; `llm_service.ts` ya no la conoce.
 */
export const LLM_PROVIDER_DEFAULTS: Record<string, { url: string; model: string }> = {
  llama_cpp: { url: 'http://127.0.0.1:8080', model: 'Qwen3.8-27B' },
  ollama: { url: 'http://localhost:11434', model: 'qwen2.5-coder:7b' },
  openai_compatible: { url: 'http://localhost:1234', model: 'local-model' },
};

export const DEFAULT_POSTGRES_HOST = 'localhost';
export const DEFAULT_POSTGRES_PORT = 5432;
export const DEFAULT_POSTGRES_DB = 'democratizacion_metadatos';

export interface CorporateRoleDefinition {
  name: string;
  label: string;
  category: 'C-Level' | 'Finanzas' | 'Talento' | 'Datos' | 'TI' | 'Seguridad' | 'Admin' | 'General';
  description: string;
  badgeColor: string;
}

/**
 * Estado explicito de "esta cuenta no tiene rol". NO es un rol del catalogo ni
 * un alias de uno: el backend devuelve `role_name = null` en ese caso y antes
 * cada pantalla se inventaba un nombre ("Usuario", "Super Administrador") que
 * nadie le habia asignado a esa persona.
 */
export const NO_ROLE_LABEL = 'Sin rol asignado';

/**
 * El rol de plataforma, con el nombre exacto del catalogo. Se declara una vez y
 * por encima de CORPORATE_ROLES porque `resolveRoleLabel` lo necesita aunque la
 * cuenta no tenga role_name: `is_admin` es un hecho persistido, esa persona
 * tiene privilegios reales, y el nombre que corresponde ya existe en el
 * catalogo.
 */
export const PLATFORM_ADMIN_ROLE_NAME = 'Administrador de Plataforma';

/** Lo unico que necesita el frontend para nombrar un rol. */
export interface RoleLabelSource {
  role_name?: string | null;
  is_admin?: boolean | null;
}

/**
 * Nombre del rol a mostrar. Un solo lugar decide que se ve cuando la cuenta no
 * tiene rol, para que el Header, la tabla de admin, los modales y el toast del
 * chat no puedan volver a divergir entre si.
 */
export const resolveRoleLabel = (user?: RoleLabelSource | null): string =>
  user?.role_name || (user?.is_admin ? PLATFORM_ADMIN_ROLE_NAME : NO_ROLE_LABEL);

export const CORPORATE_ROLES: CorporateRoleDefinition[] = [
  {
    name: PLATFORM_ADMIN_ROLE_NAME,
    label: PLATFORM_ADMIN_ROLE_NAME,
    category: 'Admin',
    description: 'Acceso total a gobernanza RBAC, gestión de usuarios, conexiones y auditoría',
    badgeColor: 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/30'
  },
  {
    name: 'Director Ejecutivo (C-Level)',
    label: 'Director Ejecutivo (C-Level)',
    category: 'C-Level',
    description: 'Visión macro estratégica, rentabilidad global y alertas de riesgo de negocio',
    badgeColor: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30'
  },
  {
    name: 'Analista Financiero & Comercial',
    label: 'Analista Financiero & Comercial',
    category: 'Finanzas',
    description: 'Ventas, facturación, márgenes y rentabilidad comercial',
    badgeColor: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
  },
  {
    name: 'Gerente de Talento & Operaciones',
    label: 'Gerente de Talento & Operaciones',
    category: 'Talento',
    description: 'Clima laboral, encuestas organizacionales y métricas operacionales',
    badgeColor: 'bg-pink-500/10 text-pink-700 dark:text-pink-400 border-pink-500/30'
  },
  {
    name: 'Analista de Datos & BI',
    label: 'Analista de Datos & BI',
    category: 'Datos',
    description: 'Exploración multidimensional, cruce de métricas y correlaciones estadísticas',
    badgeColor: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-500/30'
  },
  {
    name: 'Ingeniero de Infraestructura & TI',
    label: 'Ingeniero de Infraestructura & TI',
    category: 'TI',
    description: 'Monitoreo de servidores, consumo de recursos y rendimiento de consultas',
    badgeColor: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border-cyan-500/30'
  },
  {
    name: 'Oficial de Cumplimiento & Seguridad',
    label: 'Oficial de Cumplimiento & Seguridad (DPO)',
    category: 'Seguridad',
    description: 'Vigilancia de trazabilidad, cumplimiento de normativas de datos y auditoría',
    badgeColor: 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30'
  },
  {
    name: 'Usuario Consultor',
    label: 'Usuario Consultor',
    category: 'General',
    description: 'Perfil inicial por defecto con acceso de solo lectura básica',
    badgeColor: 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/30'
  }
];

export const getRoleBadgeStyle = (roleName?: string | null): string => {
  // "Sin rol asignado" no es un rol desconocido: es una cuenta a la que hay que
  // asignarle uno. Se pinta como advertencia para que el admin lo vea en la
  // tabla y no lo lea como un rol mas.
  if (roleName === NO_ROLE_LABEL) {
    return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30';
  }
  const match = CORPORATE_ROLES.find((r) => r.name === roleName);
  return match?.badgeColor || 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/30';
};
