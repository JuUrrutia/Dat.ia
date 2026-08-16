export interface User {
  id: number;
  username: string;
  email?: string;
  is_admin: boolean;
  role_name?: string;
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

export interface QueryResult {
  id: string;
  question: string;
  timestamp: string;
  summary_text: string;
  executive_report?: ExecutiveReport;
  kpis: KPICard[];
  gauges?: MetricGauge[];
  chart_type: 'bar' | 'line' | 'area' | 'pie' | 'donut' | 'radar' | 'gauge';
  chart_option: any; // ECharts option
  data_columns: string[];
  data_rows: Record<string, any>[];
  traceability: TraceabilityAudit;
  pipeline_source?: 'backend' | 'llm_direct' | 'fallback';
  response_type?: 'data_analysis' | 'advisory' | 'explanation' | 'hybrid';
  conversational_response?: string; // Respuesta conversacional rica (advisory/explanation/hybrid)
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
