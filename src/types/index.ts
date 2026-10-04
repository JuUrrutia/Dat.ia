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
  result_snapshot?: string | null;
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
  audit_log_id?: number;
  target_database?: string | null;
}

export interface PresentationHints {
  show_executive_report?: boolean;
  show_kpis?: boolean;
  show_chart?: boolean;
  preferred_view?: 'assistant' | 'report' | 'table';
  summary_style?: 'concise' | 'detailed' | 'executive';
}

export interface QueryResult {
  id: string;
  question: string;
  timestamp: string;
  summary_text: string;
  executive_report?: ExecutiveReport;
  kpis: KPICard[];
  chart_type: 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'none';
  chart_option: any; // ECharts option
  data_columns: string[];
  data_rows: Record<string, any>[];
  traceability: TraceabilityAudit;
  pipeline_source?: 'backend' | 'llm_direct' | 'fallback';
  response_type?: 'data_analysis' | 'advisory' | 'explanation' | 'report' | 'hybrid' | 'greeting' | 'error' | 'out_of_scope';
  conversational_response?: string; // Respuesta conversacional estructurada
  grounding_info?: string; // Información de las tablas o registros reales de la BD consultados
  presentation_hints?: PresentationHints;
  thinking_process?: string;
  suggested_questions?: string[];
  clarification_options?: string[];
  anomalies_detected?: Array<{
    column: string;
    row_index: number;
    entity: string;
    value: number;
    mean: number;
    stdev: number;
    z_score: number;
    direction: 'spike' | 'drop';
    description: string;
    probable_cause: string;
  }>;
  sql_explanation?: string;
  audit_log_id?: number;
  nulls_detected?: {
    has_nulls: boolean;
    table_name: string;
    columns_with_nulls: string[];
    null_rows_count: number;
    total_rows: number;
    options: Array<{
      action: string;
      label: string;
      prompt: string;
    }>;
  };
}

/**
 * Prediccion del proximo periodo.
 *
 * `mape` y `band_pct` NO son opcionales ni decorativos: son el error historico
 * medido por replay sobre la serie real. Un forecast sin ellos es un numero sin
 * informacion, asi que la UI esta obligada a mostrarlos.
 */
export interface ForecastCard {
  available: boolean;
  period?: string | null;
  point?: number | null;
  lower?: number | null;
  upper?: number | null;
  band_pct?: number | null;
  mape?: number | null;
  method?: string | null;
  n_periods: number;
  n_backtests: number;
  reliable: boolean;
  has_gaps: boolean;
  reason?: string | null;
  table?: string | null;
  metric_column?: string | null;
  date_column?: string | null;
  income_only: boolean;
  series: Record<string, any>[];
  sql?: string | null;
}

export interface RetentionTier {
  tier: string;
  casos: number;
  retornaron: number;
  /** `null` = evidencia insuficiente. NO es 0%: `0%` es una afirmacion, `null` es "no se". */
  prob?: number | null;
  evidence_sufficient: boolean;
}

export interface RetentionClient {
  entity: string;
  months_active: number;
  last_purchase: string;
  months_since_last: number;
  revenue: number;
  revenue_share: number;
  tier: string;
  return_prob?: number | null;
  evidence_sufficient: boolean;
}

export interface RetentionReport {
  total_clients: number;
  total_revenue: number;
  last_period?: string | null;
  tiers: RetentionTier[];
  top: RetentionClient[];
  truncated_by_limit: boolean;
  entity_column?: string | null;
  metric_column?: string | null;
  date_column?: string | null;
  income_only: boolean;
  sql?: string | null;
  reason?: string | null;
}

export interface DataQualityFinding {
  check: string;
  severity: 'ALTO' | 'MEDIO' | 'BAJO';
  detail: string;
  count?: number | null;
}

export interface PredictionResult {
  question?: string | null;
  forecast?: ForecastCard | null;
  retention?: RetentionReport | null;
  /** Fallos parciales: son dos predicciones independientes y una puede fallar sin que la otra importe. */
  errors?: string[];
  data_quality: DataQualityFinding[];
  audit_log_id?: number | null;
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
