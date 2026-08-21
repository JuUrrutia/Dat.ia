export interface User {
  id: number;
  username: string;
  email?: string;
  is_admin: boolean;
  role_name?: string;
  must_change_password?: boolean;
  failed_login_attempts?: number;
  locked_until?: string | null;
}

export interface UserSession {
  id: number;
  user_id: number;
  username?: string;
  jti: string;
  created_at: string;
  last_seen_at: string;
  ip_address?: string;
  user_agent?: string;
  is_revoked: boolean;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  user_id?: number | null;
  username: string;
  user_role?: string | null;
  question_prompt: string;
  sql_generated?: string | null;
  validation_status: string;
  target_database?: string | null;
  execution_time_ms: number;
  rows_returned: number;
  error_message?: string | null;
}

export interface AuditLogsPage {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: AuditLog[];
}

export interface AuditFilterParams {
  start_date?: string;
  end_date?: string;
  username?: string;
  target_database?: string;
  validation_status?: string;
  page?: number;
  page_size?: number;
}

export interface PasswordResetResult {
  message: string;
  username: string;
  temporary_password: string;
}

export interface KPICard {
  title: string;
  value: string;
  subtitle?: string;
  change_direction?: 'positive' | 'negative' | 'neutral';
}

export interface MetricGauge {
  title: string;
  percentage: number;
  value_label: string;
  target_label: string;
  color?: string;
}

export interface ExecutiveReport {
  overview: string;
  key_findings: string[];
  recommendations: string[];
  risk_level?: 'BAJO' | 'MEDIO' | 'ALTO' | 'CRITICO';
  business_impact?: string;
}

export interface TraceabilityAudit {
  sql_executed: string;
  execution_time_ms: number;
  rows_returned: number;
  validation_status: string;
  schema_tables_used: string[];
  explanation: string;
}

export interface PresentationHints {
  show_executive_report: boolean;
  show_kpis: boolean;
  show_gauges: boolean;
  show_chart: boolean;
  preferred_view: 'studio' | 'report' | 'table' | 'assistant';
  summary_style: 'concise' | 'detailed' | 'executive';
}

export interface QueryResult {
  id: string;
  question: string;
  timestamp: string;
  summary_text: string;
  executive_report?: ExecutiveReport;
  kpis: KPICard[];
  gauges?: MetricGauge[];
  chart_type: 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'radar' | 'gauge' | 'none';
  chart_option: any; // ECharts option
  data_columns: string[];
  data_rows: Record<string, any>[];
  traceability: TraceabilityAudit;
  pipeline_source?: 'backend' | 'llm_direct' | 'fallback';
  response_type?: 'data_analysis' | 'advisory' | 'explanation' | 'report' | 'hybrid' | 'greeting';
  conversational_response?: string; // Respuesta conversacional estructurada
  grounding_info?: string; // Información de las tablas o registros reales de la BD consultados
  presentation_hints?: PresentationHints;
}

export interface AppSettings {
  llm_provider: 'llama_cpp' | 'ollama' | 'openai_compatible' | 'custom';
  ollama_url: string;
  ollama_model: string;
  postgres_host: string;
  postgres_port: number;
  postgres_db: string;
  auto_detect_llm: boolean;
}

export interface ComponentHealth {
  name: string;
  type: 'llm' | 'metadata_db' | 'connector';
  status: 'OPERATIVO' | 'DEGRADADO' | 'CRITICO' | 'ERROR';
  latency_ms: number;
  message: string;
  details?: Record<string, any>;
}

export interface SystemHealthResponse {
  status: 'OPERATIVO' | 'DEGRADADO' | 'CRITICO';
  timestamp: string;
  llm_engine: ComponentHealth;
  metadata_db: ComponentHealth;
  corporate_connectors: ComponentHealth[];
  total_active_connectors: number;
  healthy_connectors_count: number;
}

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface ToastNotification {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}
