/**
 * Centralized Application Constants for Frontend
 */

export const DEFAULT_LLM_PROVIDER = 'llama_cpp';
export const DEFAULT_OLLAMA_URL = 'http://127.0.0.1:8080';
export const DEFAULT_LLM_MODEL = 'qwen2.5-coder:7b';

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

export const CORPORATE_ROLES: CorporateRoleDefinition[] = [
  {
    name: 'Administrador de Plataforma',
    label: 'Administrador de Plataforma',
    category: 'Admin',
    description: 'Acceso total a gobernanza RBAC, gestión de usuarios, conexiones y auditoría',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30'
  },
  {
    name: 'Director Ejecutivo (C-Level)',
    label: 'Director Ejecutivo (C-Level)',
    category: 'C-Level',
    description: 'Visión macro estratégica, rentabilidad global y alertas de riesgo de negocio',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30'
  },
  {
    name: 'Analista Financiero & Comercial',
    label: 'Analista Financiero & Comercial',
    category: 'Finanzas',
    description: 'Ventas, facturación, márgenes y rentabilidad comercial',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
  },
  {
    name: 'Gerente de Talento & Operaciones',
    label: 'Gerente de Talento & Operaciones',
    category: 'Talento',
    description: 'Clima laboral, encuestas organizacionales y métricas operacionales',
    badgeColor: 'bg-pink-500/10 text-pink-400 border-pink-500/30'
  },
  {
    name: 'Analista de Datos & BI',
    label: 'Analista de Datos & BI',
    category: 'Datos',
    description: 'Exploración multidimensional, cruce de métricas y correlaciones estadísticas',
    badgeColor: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
  },
  {
    name: 'Ingeniero de Infraestructura & TI',
    label: 'Ingeniero de Infraestructura & TI',
    category: 'TI',
    description: 'Monitoreo de servidores, consumo de recursos y rendimiento de consultas',
    badgeColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
  },
  {
    name: 'Oficial de Cumplimiento & Seguridad',
    label: 'Oficial de Cumplimiento & Seguridad (DPO)',
    category: 'Seguridad',
    description: 'Vigilancia de trazabilidad, cumplimiento de normativas de datos y auditoría',
    badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/30'
  },
  {
    name: 'Usuario Consultor',
    label: 'Usuario Consultor',
    category: 'General',
    description: 'Perfil inicial por defecto con acceso de solo lectura básica',
    badgeColor: 'bg-gray-500/10 text-gray-400 border-gray-500/30'
  }
];

export const getRoleBadgeStyle = (roleName?: string): string => {
  const match = CORPORATE_ROLES.find(r => r.name === roleName || (r.name.startsWith("Analista Finan") && roleName === "Economista") || (r.name.startsWith("Ingeniero") && roleName === "TI"));
  return match?.badgeColor || 'bg-gray-500/10 text-gray-400 border-gray-500/30';
};
