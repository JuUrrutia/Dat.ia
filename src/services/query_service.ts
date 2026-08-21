import { apiClient } from './api_client';
import { QueryResult, AppSettings } from '../types';
import { llmClientService } from './llm_service';
import { DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER } from '../constants';

export const queryService = {
  /**
   * Fetches dynamic, table-specific question suggestions from the backend API.
   */
  async getSuggestions(userRole: string = 'Economista'): Promise<string[]> {
    try {
      const res = await apiClient.get('/chat/suggestions', {
        params: { user_role: userRole }
      });
      if (res.data && Array.isArray(res.data.suggestions) && res.data.suggestions.length > 0) {
        return res.data.suggestions;
      }
    } catch {
      // Backend offline fallback
    }

    if (userRole === 'Usuario') {
      return [
        '¿Qué información puedo consultar con mi perfil Usuario?',
        '¿Cómo solicito acceso a tablas adicionales de la base de datos?'
      ];
    }

    return [
      '📊 Resumen de registros y métricas principales',
      '📈 Tendencias y distribución de datos acumulados',
      '📋 Listado detallado de tablas autorizadas',
      '💡 Consultas analíticas para toma de decisiones'
    ];
  },


  /**
   * Sends a user query through the intelligent multi-tier pipeline:
   * 1. Backend real (Python FastAPI + SQLite demo_corporativa.db + AST validation + LLM)
   * 2. Direct LLM completion (if backend is offline, queries local llama.cpp/Ollama directly for dynamic AI answer)
   * 3. Fallback offline demo response (if both backend and LLM are down)
   */
  async sendQuery(
    question: string,
    userRole: string = 'Economista',
    settings?: AppSettings
  ): Promise<QueryResult> {

    // Tier 1: Try Backend FastAPI (authenticated pipeline with SQL execution on connected database)
    try {
      const res = await apiClient.post('/chat/query', {
        question,
        connection_id: 1,
      });

      if (res.data && res.data.summary_text) {
        return {
          id: `res-${Date.now()}`,
          question: res.data.question,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          summary_text: res.data.summary_text,
          executive_report: res.data.executive_report,
          kpis: res.data.kpis || [],
          gauges: res.data.gauges || [],
          chart_type: res.data.chart_type || 'bar',
          chart_option: res.data.chart_option || {},
          data_columns: res.data.data_columns || [],
          data_rows: res.data.data_rows || [],
          traceability: res.data.traceability,
          pipeline_source: 'backend',
          response_type: res.data.response_type || 'data_analysis',
          conversational_response: res.data.conversational_response || undefined,
          grounding_info: res.data.grounding_info || undefined,
          presentation_hints: res.data.presentation_hints || undefined,
        };
      }
    } catch (err: any) {
      if (err?.response?.status === 401) {
        return {
          id: `res-${Date.now()}`,
          question,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          summary_text: '⚠️ Tu sesión ha expirado o no está autorizada. Por favor, cierra sesión e inicia nuevamente para continuar consultando los datos corporativos.',
          kpis: [],
          chart_type: 'none',
          chart_option: {},
          data_columns: [],
          data_rows: [],
          traceability: {
            sql_executed: '-- Solicitud no autorizada (HTTP 401)',
            execution_time_ms: 0,
            rows_returned: 0,
            validation_status: 'RECHAZADO_AUTH',
            schema_tables_used: [],
            explanation: 'La solicitud fue rechazada por falta de autenticación o token JWT expirado.',
          },
          pipeline_source: 'backend',
          response_type: 'error',
        };
      }
      // Backend not running/unreachable — fall through to Tier 2
    }

    // Tier 2: Direct Local LLM query (when backend is offline but llama.cpp / Ollama is running)
    const provider = settings?.llm_provider || DEFAULT_LLM_PROVIDER;
    const baseUrl = settings?.ollama_url || DEFAULT_OLLAMA_URL;
    const modelName = settings?.ollama_model || DEFAULT_LLM_MODEL;

    const qLower = question.toLowerCase();
    const isAdvisoryQuery = [
      'idea', 'ideas', 'recomienda', 'recomendacion', 'recomendaciones',
      'sugerencia', 'sugerencias', 'estrategia', 'estrategias', 'consejo', 'consejos',
      'productividad', 'productivo', 'cómo mejorar', 'como mejorar', 'optimizar', 'ayuda'
    ].some((k) => qLower.includes(k));

    try {
      const promptLLM = isAdvisoryQuery
        ? `Pregunta del usuario (${userRole}): "${question}".
Eres un Asesor Ejecutivo Senior y Consultor Corporativo.
Responde con ideas concretas, accionables y de alto valor estratégico para la empresa.
Usa formato Markdown elegante (## Título, ### 1. Nombre de la Idea, **Diagnóstico**, **Acción**, **Impacto Esperado**). NO generes código SQL.`
        : `Pregunta del usuario (${userRole}): "${question}".
Analiza la solicitud y propone una respuesta analítica conceptual en español para el rol ${userRole}.
Si corresponde una consulta SQL, incluye la consulta propuesta en un bloque \`\`\`sql SELECT ... \`\`\`.`;

      const llmResult = await llmClientService.testCompletion(promptLLM, provider, baseUrl, modelName);

      if (llmResult.success && llmResult.completion_text && !llmResult.completion_text.includes('No se pudo conectar')) {
        // Extract SQL if present in LLM completion
        const sqlMatch = llmResult.completion_text.match(/```sql\s*([\s\S]*?)\s*```/i);
        const extractedSql = sqlMatch ? sqlMatch[1].trim() : '-- Generado por IA Local Directa';
        
        // Clean narrative summary (remove SQL block)
        const narrativeText = llmResult.completion_text.replace(/```sql[\s\S]*?```/gi, '').trim();

        if (isAdvisoryQuery) {
          return {
            id: `res-${Date.now()}`,
            question,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            summary_text: `Asesoría Estratégica generada por IA Local (${modelName.split('/')[0] || 'Qwen2.5'}).`,
            conversational_response: narrativeText,
            kpis: [],
            gauges: [],
            chart_type: 'none',
            chart_option: {},
            data_columns: [],
            data_rows: [],
            traceability: {
              sql_executed: '-- MODO ASISTENTE ESTRATÉGICO DIRECTO',
              execution_time_ms: llmResult.latency_ms,
              rows_returned: 0,
              validation_status: 'APROBADO_LLM_DIRECTO',
              schema_tables_used: ['consultoria_estrategica'],
              explanation: `Respuesta de asesoría estratégica generada en vivo por la IA Local (${modelName}).`
            },
            pipeline_source: 'llm_direct',
            response_type: 'advisory',
            grounding_info: `Generado con IA Local (${modelName})`,
            presentation_hints: {
              show_executive_report: false,
              show_kpis: false,
              show_gauges: false,
              show_chart: false,
              preferred_view: 'assistant' as const,
              summary_style: 'detailed' as const,
            },
          };
        }

        return {
          id: `res-${Date.now()}`,
          question,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          summary_text: `🤖 [IA Local ${modelName.split('/')[0] || 'Qwen'}]: ${narrativeText || 'Consulta analizada por la IA.'}\n\n⚠️ *Nota:* Para ejecutar la consulta sobre los datos reales de la base de datos y ver la tabla de resultados, inicia el backend FastAPI ejecutando \`py main.py\` en la carpeta backend.`,
          kpis: [
            { title: 'Inferencia LLM', value: `${(llmResult.latency_ms / 1000).toFixed(1)}s`, subtitle: 'Tiempo Inferencia', change_direction: 'positive' },
            { title: 'Modelo Invocado', value: modelName.split('/')[0] || 'Qwen2.5', subtitle: '100% Local / Offline', change_direction: 'positive' },
            { title: 'Estado Backend', value: 'OFFLINE', subtitle: 'Ejecuta py main.py', change_direction: 'neutral' }
          ],
          chart_type: 'bar',
          chart_option: { xAxis: { data: [] }, series: [] },
          data_columns: ['estado_consulta', 'accion_requerida'],
          data_rows: [{
            estado_consulta: 'Consulta SQL Generada Exitosamente',
            accion_requerida: 'Inicia el backend (py main.py) para consultar registros en vivo'
          }],
          traceability: {
            sql_executed: extractedSql,
            execution_time_ms: llmResult.latency_ms,
            rows_returned: 0,
            validation_status: 'APROBADO_LLM_DIRECTO',
            schema_tables_used: ['modo_conceptual_sin_bd'],
            explanation: `Respuesta conceptual generada en vivo por la IA Local (${modelName}). Para ejecutar la consulta SQL sobre la base de datos, se requiere el backend FastAPI.`
          },
          pipeline_source: 'llm_direct',
          response_type: 'data_analysis',
          presentation_hints: {
            show_executive_report: false,
            show_kpis: true,
            show_gauges: false,
            show_chart: false,
            preferred_view: 'studio' as const,
            summary_style: 'concise' as const,
          },
        };
      }
    } catch {
      // Direct LLM query failed or timed out — fall through to Tier 3
    }

    return queryService.getFallbackQueryResponse(question, userRole);
  },

  getFallbackQueryResponse(question: string, userRole: string): QueryResult {
    // Check "Usuario" role initial state
    if (userRole === 'Usuario') {
      return {
        id: `res-${Date.now()}`,
        question,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        summary_text: 'Tu cuenta se encuentra registrada con el perfil inicial "Usuario". Un Administrador debe asignarte tu perfil definitivo para acceder a las bases de datos de la empresa.',
        kpis: [
          { title: 'Estado Cuenta', value: 'REGISTRADO', subtitle: 'Pendiente Rol', change_direction: 'neutral' },
          { title: 'Permisos BD', value: '0 Tablas', subtitle: 'Gobernanza RBAC', change_direction: 'negative' }
        ],
        chart_type: 'bar',
        chart_option: { xAxis: { data: [] }, series: [] },
        data_columns: ['estado', 'mensaje'],
        data_rows: [{ estado: 'PENDIENTE', mensaje: 'Contacta al Administrador para habilitar tu acceso.' }],
        traceability: {
          sql_executed: '-- CONSULTA BLOQUEADA: PERFIL USUARIO SIN ASIGNACIÓN',
          execution_time_ms: 0,
          rows_returned: 0,
          validation_status: 'RECHAZADO_RBAC',
          schema_tables_used: [],
          explanation: 'Cuenta recién registrada. Carece de permisos temáticos hasta asignación por Administrador.'
        },
        pipeline_source: 'fallback',
        response_type: 'data_analysis',
      };
    }

    // Standard LLM Offline response (no simulated fake data or queries)
    return {
      id: `res-${Date.now()}`,
      question,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      summary_text: 'IA local no disponible. Conecte Ollama/llama.cpp para ejecutar consultas.',
      kpis: [
        { title: 'Estado IA Local', value: 'DESCONECTADO', subtitle: 'Conecte Ollama o llama.cpp', change_direction: 'negative' }
      ],
      chart_type: 'none',
      chart_option: {},
      data_columns: [],
      data_rows: [],
      traceability: {
        sql_executed: '-- CONSULTA NO GENERADA: IA LOCAL DESCONECTADA',
        execution_time_ms: 0,
        rows_returned: 0,
        validation_status: 'RECHAZADO (IA Local No Disponible)',
        schema_tables_used: [],
        explanation: 'Se requiere un servidor LLM local activo (Ollama en :11434 o llama.cpp en :8080) para traducir lenguaje natural a SQL.'
      },
      pipeline_source: 'fallback',
      response_type: 'data_analysis',
    };
  }
};
