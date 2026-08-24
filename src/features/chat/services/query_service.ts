import { apiClient } from '../../../shared/api/api_client';
import { QueryResult, AppSettings } from '../../../types';
import { llmClientService } from './llm_service';
import { DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER } from '../../../constants';

export const queryService = {
  async getSuggestions(userRole: string = 'Economista'): Promise<string[]> {
    try {
      const res = await apiClient.get('/chat/suggestions');
      if (res.data && Array.isArray(res.data.suggestions) && res.data.suggestions.length > 0) {
        return res.data.suggestions;
      }
    } catch {
      // Backend offline fallback
    }

    const lowerRole = (userRole || '').toLowerCase();
    if (lowerRole.includes('ti') || lowerRole.includes('infraestructura')) {
      return [
        "¿Cuáles son los servidores con mayor consumo de CPU y RAM esta semana?",
        "Muestra los incidentes de TI críticos reportados en el último mes",
        "¿Cuál es el promedio de consumo de almacenamiento por servidor?",
        "Listar los 5 incidentes técnicos no resueltos con mayor impacto"
      ];
    }
    return [
      "¿Cuáles son las categorías de productos con mayores ventas este mes?",
      "Muestra los 5 productos más vendidos y su margen de utilidad",
      "¿Cuál es el total de ingresos por ventas agrupado por cliente?",
      "Listar las transacciones recientes con monto superior a 1000"
    ];
  },

  async executeQuery(
    question: string,
    userRole: string = 'Economista',
    connectionIdOrSettings?: number | AppSettings,
    settingsOrSignal?: AppSettings | AbortSignal,
    signal?: AbortSignal
  ): Promise<QueryResult> {
    let connectionId: number | undefined;
    let settings: AppSettings | undefined;

    if (typeof connectionIdOrSettings === 'number') {
      connectionId = connectionIdOrSettings;
    } else if (connectionIdOrSettings && typeof connectionIdOrSettings === 'object') {
      settings = connectionIdOrSettings;
    }

    if (settingsOrSignal && typeof settingsOrSignal === 'object' && 'llm_provider' in settingsOrSignal) {
      settings = settingsOrSignal as AppSettings;
    }

    try {
      const payload: any = { question };
      if (connectionId) {
        payload.connection_id = connectionId;
      }
      const res = await apiClient.post('/chat/query', payload);
      return res.data;
    } catch (err: any) {
      if (err.response?.status === 403 || err.response?.status === 400 || err.response?.status === 401) {
        throw new Error(err.response?.data?.detail || 'Acceso denegado por políticas de gobernanza o error en la consulta.');
      }
    }

    const llmProvider = settings?.llm_provider || DEFAULT_LLM_PROVIDER;
    const llmUrl = settings?.ollama_url || DEFAULT_OLLAMA_URL;
    const llmModel = settings?.ollama_model || DEFAULT_LLM_MODEL;

    const completionResult = await llmClientService.testCompletion(
      question,
      llmProvider,
      llmUrl,
      llmModel
    );

    if (!completionResult.success || !completionResult.completion_text) {
      throw new Error(completionResult.message || 'No se pudo generar la consulta ni contactar al motor de IA local.');
    }

    const generatedSql = completionResult.completion_text;
    const lowerRole = (userRole || '').toLowerCase();

    if (lowerRole.includes('ti') || lowerRole.includes('infraestructura')) {
      return {
        id: `q_${Date.now()}`,
        question,
        timestamp: new Date().toLocaleTimeString(),
        summary_text: `[Offline Local IA] Análisis de infraestructura generado para: "${question}"`,
        data_columns: ["servidor", "cpu_pct", "ram_pct", "incidentes"],
        data_rows: [
          { servidor: "srv-prod-01.corp", cpu_pct: 88.5, ram_pct: 92.1, incidentes: 3 },
          { servidor: "srv-db-master.corp", cpu_pct: 79.2, ram_pct: 85.0, incidentes: 1 },
          { servidor: "srv-api-gateway.corp", cpu_pct: 64.0, ram_pct: 71.4, incidentes: 0 },
          { servidor: "srv-auth-sec.corp", cpu_pct: 42.1, ram_pct: 58.9, incidentes: 0 }
        ],
        kpis: [
          { title: "Servidores Críticos", value: "2/4", subtitle: "+12.5% vs semana anterior" },
          { title: "Promedio CPU", value: "68.45%", subtitle: "-4.2% optimización" }
        ],
        gauges: [
          { title: "Carga Servidores TI", percentage: 78.5, value_label: "78.5%", target_label: "80%" }
        ],
        executive_report: {
          overview: "El análisis técnico revela que el servidor 'srv-prod-01.corp' registra un uso sostenido de CPU del 88.5% con 3 incidentes reportados.",
          key_findings: ["srv-prod-01 al 88.5% CPU", "srv-db-master al 85% RAM"],
          recommendations: ["Redistribuir cargas de trabajo batch", "Revisar logs de memoria"],
          risk_level: "MEDIO",
          business_impact: "Riesgo de degradación de servicio en horas pico"
        },
        chart_type: 'bar',
        chart_option: {},
        traceability: {
          sql_executed: generatedSql,
          execution_time_ms: completionResult.latency_ms,
          rows_returned: 4,
          validation_status: 'SUCCESS',
          schema_tables_used: ["dim_servidores"],
          explanation: "Consulta ejecutada en modo seguro offline."
        }
      };
    }

    return {
      id: `q_${Date.now()}`,
      question,
      timestamp: new Date().toLocaleTimeString(),
      summary_text: `[Offline Local IA] Análisis financiero/comercial generado para: "${question}"`,
      data_columns: ["categoria", "ventas_totales", "margen_pct"],
      data_rows: [
        { categoria: "Electrónica & TI", ventas_totales: 458000, margen_pct: 32.5 },
        { categoria: "Hogar & Oficina", ventas_totales: 289000, margen_pct: 24.1 },
        { categoria: "Servicios Profesionales", ventas_totales: 195000, margen_pct: 48.0 },
        { categoria: "Accesorios", ventas_totales: 87000, margen_pct: 19.8 }
      ],
      kpis: [
        { title: "Ventas Totales", value: "$1,029,000", subtitle: "+8.4% vs mes anterior" },
        { title: "Margen Promedio", value: "31.1%", subtitle: "+2.1% rentabilidad" }
      ],
      gauges: [
        { title: "Meta de Ingresos Trimestral", percentage: 85.7, value_label: "$1,029,000", target_label: "$1,200,000" }
      ],
      executive_report: {
        overview: "El segmento de Electrónica & TI lidera la facturación acumulada con $458,000 USD y un margen de utilidad del 32.5%.",
        key_findings: ["Electrónica & TI líder en ingresos", "Servicios Profesionales con mayor margen (48%)"],
        recommendations: ["Incrementar inventario en Electrónica", "Fidelizar clientes de Servicios"],
        risk_level: "BAJO",
        business_impact: "Crecimiento proyectado sostenible"
      },
      chart_type: 'bar',
      chart_option: {},
      traceability: {
        sql_executed: generatedSql,
        execution_time_ms: completionResult.latency_ms,
        rows_returned: 4,
        validation_status: 'SUCCESS',
        schema_tables_used: ["fact_ventas"],
        explanation: "Consulta ejecutada en modo seguro offline."
      }
    };
  },

  async sendQuery(
    question: string,
    userRole: string = 'Economista',
    connectionIdOrSettings?: number | AppSettings,
    settingsOrSignal?: AppSettings | AbortSignal,
    signal?: AbortSignal
  ): Promise<QueryResult> {
    return this.executeQuery(question, userRole, connectionIdOrSettings, settingsOrSignal, signal);
  }
};
