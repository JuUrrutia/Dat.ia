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

const INFERENCE_TIMEOUT_MS = 300_000;

export const llmClientService = {
  async testConnection(
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMConnectionTestResult> {
    try {
      const res = await apiClient.post<LLMConnectionTestResult>('/llm/test-connection', {
        provider,
        base_url: baseUrl,
        model_name: modelName
      });
      return res.data;
    } catch {
      // Direct fetch fallback
    }

    const primaryUrl = baseUrl.replace(/\/+$/, '');
    const candidateUrls = [
      primaryUrl,
      'http://127.0.0.1:8080',
      'http://localhost:8080',
      'http://localhost:11434',
      'http://localhost:1234',
    ].filter((u, idx, arr) => arr.indexOf(u) === idx);

    for (const url of candidateUrls) {
      const candStart = Date.now();

      if (provider === 'ollama' || url.includes('11434')) {
        try {
          const res = await fetch(`${url}/api/tags`, { signal: AbortSignal.timeout(3000) });
          if (res.ok) {
            const data = await res.json();
            const models = (data.models || []).map((m: any) => m.name || m.model || '');
            return {
              success: true,
              message: `Conectado exitosamente con Ollama en ${url}.`,
              available_models: models.length > 0 ? models : [modelName],
              latency_ms: Date.now() - candStart,
            };
          }
        } catch { /* continue */ }
      }

      for (const endpoint of [`${url}/v1/models`, `${url}/props`, `${url}/health`, `${url}/slots`]) {
        try {
          const res = await fetch(endpoint, { signal: AbortSignal.timeout(3000) });
          if (res.ok) {
            const data = await res.json().catch(() => ({}));
            let models: string[] = [];

            if (data.data && Array.isArray(data.data)) {
              models = data.data.flatMap((m: any) => (m.id ? [m.id] : []));
            } else if (data.default_generation_settings || data.model) {
              const mName = data.default_generation_settings?.model || data.model || '';
              if (mName) models = [mName];
            }

            if (models.length === 0) models = [modelName || 'local-model'];
            const provLabel = url.includes('8080') || endpoint.includes('props') ? 'llama.cpp' : 'servidor LLM local';

            return {
              success: true,
              message: `Conectado exitosamente con ${provLabel} en ${url}.`,
              available_models: models,
              latency_ms: Date.now() - candStart,
            };
          }
        } catch { /* continue */ }
      }
    }

    return {
      success: false,
      message: `No se pudo contactar al servidor LLM en ${primaryUrl} ni en puertos 8080/11434/1234. Verifica que llama.exe serve u Ollama esté activo.`,
      available_models: [modelName],
      latency_ms: 0,
    };
  },

  async testCompletion(
    prompt: string,
    provider: string,
    baseUrl: string,
    modelName: string
  ): Promise<LLMCompletionTestResult> {
    try {
      const res = await apiClient.post<LLMCompletionTestResult>('/llm/test-completion', {
        prompt,
        provider,
        base_url: baseUrl,
        model_name: modelName
      });
      return res.data;
    } catch {
      // Direct fetch fallback
    }

    const url = baseUrl.replace(/\/+$/, '');
    const startTime = Date.now();
    const systemPrompt = 'Eres un asistente experto en SQL corporativo. Genera una consulta SQL limpia en dialecto SQLite para la pregunta dada. Responde de forma concisa.';
    const cleanThinkTags = (text: string) => text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

    if (provider === 'ollama' || url.includes('11434')) {
      return this._tryOllamaGenerate(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags)
        .catch(() => this._tryOpenAIChat(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags))
        .catch(() => this._buildErrorResult(url, startTime));
    }

    return this._tryOpenAIChat(url, modelName, prompt, systemPrompt, startTime, cleanThinkTags)
      .catch(() => this._tryNativeCompletion(url, prompt, systemPrompt, startTime, cleanThinkTags))
      .catch(() => this._buildErrorResult(url, startTime));
  },

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
      completion_text: '',
      latency_ms: Date.now() - startTime,
      message: `IA local no disponible. Conecte Ollama/llama.cpp en ${url} para ejecutar consultas.`
    };
  }
};
