import { apiClient } from './api_client';

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

// 5 minutes timeout for large models (27B at ~2.7 t/s can take 2-3 minutes)
const INFERENCE_TIMEOUT_MS = 300_000;

/**
 * LLM Client Service that tries the backend first,
 * then falls back to direct HTTP fetch to the local LLM server.
 */
export const llmClientService = {

  /**
   * Tests connectivity to a local LLM server.
   * 1. Try via backend POST /llm/test-connection
   * 2. If backend unavailable, try direct fetch to the LLM endpoints
   */
  async testConnection(
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMConnectionTestResult> {
    // Try 1: Backend proxy
    try {
      const res = await apiClient.post<LLMConnectionTestResult>('/llm/test-connection', {
        provider,
        base_url: baseUrl,
        model_name: modelName
      });
      return res.data;
    } catch {
      // Backend not available, try direct
    }

    // Try 2: Direct fetch to LLM server
    const url = baseUrl.replace(/\/+$/, '');
    const startTime = Date.now();

    // 2a. Ollama /api/tags
    if (provider === 'ollama' || url.includes('11434')) {
      try {
        const res = await fetch(`${url}/api/tags`, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          const data = await res.json();
          const models = (data.models || []).map((m: any) => m.name || m.model || '');
          return {
            success: true,
            message: `Conectado exitosamente con Ollama en ${url}.`,
            available_models: models.length > 0 ? models : [modelName],
            latency_ms: Date.now() - startTime
          };
        }
      } catch { /* continue */ }
    }

    // 2b. OpenAI-compatible /v1/models (llama.cpp, LM Studio, vLLM)
    for (const endpoint of [`${url}/v1/models`, `${url}/props`, `${url}/health`]) {
      try {
        const res = await fetch(endpoint, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          const data = await res.json();
          let models: string[] = [];

          if (data.data && Array.isArray(data.data)) {
            models = data.data.map((m: any) => m.id || '').filter(Boolean);
          } else if (data.default_generation_settings || data.model) {
            const mName = data.default_generation_settings?.model || data.model || '';
            if (mName) models = [mName];
          }

          if (models.length === 0) models = [modelName || 'local-model'];

          return {
            success: true,
            message: `Conectado exitosamente con servidor LLM local en ${url}.`,
            available_models: models,
            latency_ms: Date.now() - startTime
          };
        }
      } catch { /* continue */ }
    }

    // All attempts failed
    return {
      success: false,
      message: `No se pudo contactar al servidor LLM en ${url}. Verifica que llama.exe serve u Ollama esté activo.`,
      available_models: [modelName],
      latency_ms: 0
    };
  },

  /**
   * Runs a real inference completion against the LLM.
   * Uses ONLY the best endpoint for the configured provider to avoid
   * sequential timeouts that double/triple wait time.
   * 
   * 1. Try via backend POST /llm/test-completion
   * 2. If backend unavailable, try direct fetch to the BEST endpoint for this provider
   */
  async testCompletion(
    prompt: string,
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMCompletionTestResult> {
    // Try 1: Backend proxy (has its own timeout handling)
    try {
      const res = await apiClient.post<LLMCompletionTestResult>('/llm/test-completion', {
        prompt,
        provider,
        base_url: baseUrl,
        model_name: modelName
      });
      return res.data;
    } catch {
      // Backend not available, try direct
    }

    // Try 2: Direct fetch — pick the RIGHT endpoint for the provider
    const url = baseUrl.replace(/\/+$/, '');
    const startTime = Date.now();
    const systemPrompt = 'Eres un asistente experto en SQL corporativo. Genera una consulta SQL limpia en dialecto SQLite para la pregunta dada. Responde de forma concisa.';

    // Helper to clean <think> tags from reasoning models
    const cleanThinkTags = (text: string) => text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

    // Determine which endpoint to use based on provider
    if (provider === 'ollama' || url.includes('11434')) {
      // Ollama: Use /api/generate (most reliable for Ollama)
      return this._tryOllamaGenerate(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags)
        .catch(() => this._tryOpenAIChat(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags))
        .catch(() => this._buildErrorResult(url, startTime));
    }

    // llama.cpp / OpenAI-compatible: Use /v1/chat/completions (modern llama.cpp default)
    return this._tryOpenAIChat(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags)
      .catch(() => this._tryNativeCompletion(url, prompt, systemPrompt, startTime, cleanThinkTags))
      .catch(() => this._buildErrorResult(url, startTime));
  },

  // OpenAI-compatible /v1/chat/completions (llama.cpp modern, LM Studio, vLLM)
  async _tryOpenAIChat(
    url: string, model: string, prompt: string, system: string,
    startTime: number, clean: (t: string) => string
  ): Promise<LLMCompletionTestResult> {
    const res = await fetch(`${url}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(INFERENCE_TIMEOUT_MS),
      body: JSON.stringify({
        model,
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: prompt }
        ],
        temperature: 0.1
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const choices = data.choices || [];
    const text = clean(choices[0]?.message?.content?.trim() || '');
    if (!text) throw new Error('Empty response');
    return {
      success: true,
      completion_text: text,
      latency_ms: Date.now() - startTime,
      message: `Inferencia completada por servidor LLM local (${model}).`
    };
  },

  // llama.cpp native /completion endpoint
  async _tryNativeCompletion(
    url: string, prompt: string, system: string,
    startTime: number, clean: (t: string) => string
  ): Promise<LLMCompletionTestResult> {
    const res = await fetch(`${url}/completion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(INFERENCE_TIMEOUT_MS),
      body: JSON.stringify({
        prompt: `System: ${system}\nUser: ${prompt}\nAssistant:`,
        temperature: 0.1,
        n_predict: 512
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const text = clean((data.content || '').trim());
    if (!text) throw new Error('Empty response');
    return {
      success: true,
      completion_text: text,
      latency_ms: Date.now() - startTime,
      message: 'Inferencia completada por llama.cpp (Endpoint Nativo /completion).'
    };
  },

  // Ollama /api/generate endpoint
  async _tryOllamaGenerate(
    url: string, model: string, prompt: string, system: string,
    startTime: number, clean: (t: string) => string
  ): Promise<LLMCompletionTestResult> {
    const res = await fetch(`${url}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(INFERENCE_TIMEOUT_MS),
      body: JSON.stringify({
        model,
        prompt,
        system,
        stream: false,
        options: { temperature: 0.1 }
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const text = clean((data.response || '').trim());
    if (!text) throw new Error('Empty response');
    return {
      success: true,
      completion_text: text,
      latency_ms: Date.now() - startTime,
      message: 'Inferencia completada por Ollama.'
    };
  },

  _buildErrorResult(url: string, startTime: number): LLMCompletionTestResult {
    return {
      success: false,
      completion_text: '-- No se pudo conectar al servidor LLM. Verifica que esté activo.',
      latency_ms: Date.now() - startTime,
      message: `No se pudo conectar al LLM en ${url}. Verifica que el servidor esté activo.`
    };
  }
};
