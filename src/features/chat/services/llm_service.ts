import { apiClient } from '../../../shared/api/api_client';

export interface LLMConnectionTestResult {
  success: boolean;
  message: string;
  available_models: string[];
  latency_ms: number;
}

export interface LLMCompletionTestResult {
  success: boolean;
  completion_text: string;
  latency_ms: number;
  message: string;
}

/**
 * El diagnostico va SIEMPRE por el backend.
 *
 * Antes, cuando el POST a `/llm/test-connection` o `/llm/test-completion`
 * fallaba, este archivo reintentaba con `fetch` DIRECTO del navegador a
 * http://127.0.0.1:8080, http://localhost:8080, http://localhost:11434 y
 * http://localhost:1234, probando /api/tags, /v1/models, /props, /health y
 * /slots, y mandando el prompt de la inferencia a /v1/chat/completions o
 * /api/generate. Eso rompia la premisa de la app: el backend es el punto de
 * control (RBAC, auditoria, allowlist anti-SSRF en
 * `llm_diagnostic_router.py`), y esas peticiones no pasaban por el. No
 * aparecian en sus logs, no cumplian la allowlist, y quedaban sujetas a CORS/CSP
 * del navegador.
 *
 * El backend cubre lo mismo: `HealthService.check_llm_connectivity` prueba el
 * `base_url` recibido y los puertos 8080/11434/1234 con esos mismos endpoints, y
 * devuelve la misma forma (`success`, `message`, `available_models`,
 * `latency_ms`). Regresiones conocidas al migrar: el backend NO recorta tags
 * `<think>` ni usa el timeout largo de 5 min del navegador, y cuando el
 * servidor no reporta modelos devuelve `[model_name]` en vez de lista vacia.
 *
 * Este modulo ahora no captura errores: un fallo del backend sube al llamador,
 * que decide si reintenta otro endpoint o muestra el error.
 */
export const llmClientService = {
  async testConnection(
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMConnectionTestResult> {
    const res = await apiClient.post<LLMConnectionTestResult>('/llm/test-connection', {
      provider,
      base_url: baseUrl,
      model_name: modelName
    });
    return res.data;
  },

  async testCompletion(
    prompt: string,
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMCompletionTestResult> {
    const res = await apiClient.post<LLMCompletionTestResult>('/llm/test-completion', {
      prompt,
      provider,
      base_url: baseUrl,
      model_name: modelName
    });
    return res.data;
  }
};
