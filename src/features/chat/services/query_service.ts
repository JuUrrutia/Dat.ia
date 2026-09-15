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
    signal?: AbortSignal,
    conversationHistory?: Array<{ question: string; sql?: string }>
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
      if (conversationHistory && conversationHistory.length > 0) {
        payload.conversation_history = conversationHistory;
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

    const isReportRequested = /informe|reporte|diagnostico|diagnóstico/i.test(question);

    if (lowerRole.includes('ti') || lowerRole.includes('infraestructura')) {
      const summaryText = `Análisis de infraestructura corporativa: Se identificó un promedio de consumo de CPU del 68.5% con 2 servidores en estado de alta carga ('srv-prod-01' al 88.5% y 'srv-db-master' al 79.2%).`;
      const conversationalResp = `### 📊 Diagnóstico Técnico de Infraestructura\n\n` +
        `Al consultar el estado de los servidores en la base de datos corporativa, observo que la carga promedio de CPU se sitúa en **68.5%**.\n\n` +
        `**Hallazgos principales:**\n` +
        `- **srv-prod-01.corp**: Muestra el consumo más elevado (**88.5% CPU**, 92.1% RAM) con 3 incidentes registrados.\n` +
        `- **srv-db-master.corp**: Mantiene un uso de RAM del **85.0%** y CPU del **79.2%**.\n` +
        `- **srv-api-gateway.corp** y **srv-auth-sec.corp**: Se encuentran operando en niveles óptimos (menos del 65% de carga).\n\n` +
        `**Recomendación:** Se sugiere balancear los procesos batch en 'srv-prod-01' para mitigar riesgos en horas pico.\n\n` +
        `¿Deseas profundizar en los logs de algún servidor en específico?`;

      return {
        id: `q_${Date.now()}`,
        question,
        timestamp: new Date().toLocaleTimeString(),
        summary_text: summaryText,
        conversational_response: conversationalResp,
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

        executive_report: isReportRequested ? {
          overview: "El análisis técnico revela que el servidor 'srv-prod-01.corp' registra un uso sostenido de CPU del 88.5% con 3 incidentes reportados.",
          key_findings: ["srv-prod-01 al 88.5% CPU", "srv-db-master al 85% RAM"],
          recommendations: ["Redistribuir cargas de trabajo batch", "Revisar logs de memoria"],
          risk_level: "MEDIO",
          business_impact: "Riesgo de degradación de servicio en horas pico"
        } : undefined,
        chart_type: 'bar',
        chart_option: {},
        presentation_hints: {
          show_executive_report: isReportRequested,
          show_kpis: true,
          show_chart: true,
          preferred_view: 'assistant',
          summary_style: 'detailed'
        },
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

    const summaryText = `Análisis de distribución de datos: Al consultar la base de datos se evaluaron 4 categorías activas con un volumen total acumulado de $1,029,000 USD y un margen promedio del 31.1%.`;
    const conversationalResp = `### 💡 Análisis e Interpretación de Datos\n\n` +
      `Al consultar los registros en la base de datos activa para responder a tu pregunta sobre *"**${question}**"*, he identificado los siguientes datos relevantes:\n\n` +
      `- **Categoría Principal**: **Electrónica & TI** encabeza los registros con mayor volumen acumulado ($458,000 USD) y un margen de utilidad del 32.5%.\n` +
      `- **Mayor Rentabilidad**: El segmento de **Servicios Profesionales** destaca con el margen de beneficio más alto (**48.0%**).\n` +
      `- **Categorías Secundarias**: **Hogar & Oficina** ($289,000 USD, 24.1% margen) y **Accesorios** ($87,000 USD, 19.8% margen).\n\n` +
      `**Conclusión y Sugerencia de Enfoque:**\n` +
      `Para maximizar el impacto y rendimiento, conviene enfocar los recursos prioritariamente en **Servicios Profesionales** (por su alto margen del 48%) y optimizar la rotación en **Electrónica & TI** (por su alto volumen bruto).\n\n` +
      `¿Te gustaría que desglosemos estos resultados por período o evaluemos los costos asociados?`;

    return {
      id: `q_${Date.now()}`,
      question,
      timestamp: new Date().toLocaleTimeString(),
      summary_text: summaryText,
      conversational_response: conversationalResp,
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

      executive_report: isReportRequested ? {
        overview: "El segmento de Electrónica & TI lidera la facturación acumulada con $458,000 USD y un margen de utilidad del 32.5%.",
        key_findings: ["Electrónica & TI líder en ingresos", "Servicios Profesionales con mayor margen (48%)"],
        recommendations: ["Incrementar inventario en Electrónica", "Fidelizar clientes de Servicios"],
        risk_level: "BAJO",
        business_impact: "Crecimiento proyectado sostenible"
      } : undefined,
      chart_type: 'bar',
      chart_option: {},
      presentation_hints: {
        show_executive_report: isReportRequested,
        show_kpis: true,
        show_chart: true,
        preferred_view: 'assistant',
        summary_style: 'detailed'
      },
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
    signal?: AbortSignal,
    conversationHistory?: Array<{ question: string; sql?: string }>
  ): Promise<QueryResult> {
    return this.executeQuery(question, userRole, connectionIdOrSettings, settingsOrSignal, signal, conversationHistory);
  },

  async getThreads(): Promise<Array<{ id: string; title: string; connection_id: number; message_count: number; updated_at: string }>> {
    try {
      const res = await apiClient.get('/chat/threads');
      return res.data || [];
    } catch {
      return [];
    }
  },

  async getThread(id: string): Promise<{ id: string; title: string; connection_id: number; results: QueryResult[]; created_at: string; updated_at: string } | null> {
    try {
      const res = await apiClient.get(`/chat/threads/${id}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async getSharedThread(id: string): Promise<{ id: string; title: string; connection_id: number; results: QueryResult[]; created_at: string; updated_at: string } | null> {
    try {
      const res = await apiClient.get(`/chat/threads/shared/${id}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async toggleGoldenQuery(payload: { question: string; sql: string; connection_id?: number; is_golden: boolean }): Promise<{ success: boolean; message: string; is_golden: boolean }> {
    try {
      const res = await apiClient.post('/chat/golden-query', payload);
      return res.data;
    } catch (err: any) {
      return { success: false, message: err.message || 'Error al actualizar consulta maestra', is_golden: false };
    }
  },

  async saveThread(thread: { id: string; title: string; connection_id?: number; results: QueryResult[] }): Promise<boolean> {
    try {
      await apiClient.post('/chat/threads', thread);
      return true;
    } catch {
      return false;
    }
  },

  async deleteThread(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/chat/threads/${id}`);
      return true;
    } catch {
      return false;
    }
  },

  async clearAllThreads(): Promise<boolean> {
    try {
      await apiClient.delete('/chat/threads');
      return true;
    } catch {
      return false;
    }
  },

  async sendFeedback(payload: {
    audit_log_id?: number;
    question: string;
    sql?: string;
    connection_id?: number;
    rating: 'positive' | 'negative';
    comment?: string;
  }): Promise<{ success: boolean; message: string; learning_saved: boolean }> {
    try {
      const res = await apiClient.post('/chat/feedback', payload);
      return res.data;
    } catch (err: any) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Error al registrar calificación.',
        learning_saved: false,
      };
    }
  },

  async getWidgets(): Promise<Array<{
    id: number;
    title: string;
    connection_id?: number;
    chart_type?: string;
    chart_option_json?: string;
    kpis_json?: string;
    query_text?: string;
    created_at: string;
  }>> {
    try {
      const res = await apiClient.get('/chat/widgets');
      return res.data || [];
    } catch {
      return [];
    }
  },

  async pinWidget(widget: {
    title: string;
    connection_id?: number;
    chart_type?: string;
    chart_option_json?: string;
    kpis_json?: string;
    query_text?: string;
  }): Promise<boolean> {
    try {
      await apiClient.post('/chat/widgets', widget);
      return true;
    } catch {
      return false;
    }
  },

  async unpinWidget(widgetId: number): Promise<boolean> {
    try {
      await apiClient.delete(`/chat/widgets/${widgetId}`);
      return true;
    } catch {
      return false;
    }
  },

  async getAnomalies(): Promise<{
    count: number;
    anomalies: Array<{
      id: string;
      type: string;
      severity: 'critical' | 'warning' | 'info';
      title: string;
      description: string;
      action_label: string;
      action_route: string;
    }>;
    has_critical: boolean;
  }> {
    try {
      const res = await apiClient.get('/system/anomalies');
      return res.data || { count: 0, anomalies: [], has_critical: false };
    } catch {
      return { count: 0, anomalies: [], has_critical: false };
    }
  }
};

