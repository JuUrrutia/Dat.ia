import { describe, it, expect, beforeEach, vi } from 'vitest';

// Sustituye los asserts por grep de `scripts/verify_no_faked_success.js` que
// exigian que estos metodos NO tuvieran un `catch` o un `|| []`. Ese check
// fallaba si alguien anadia un comentario con la palabra, y no fallaba si el
// fallback existia de otra forma.
//
// Aqui se ejecuta el metodo. El bug que estos tests protegen es concreto: un
// `catch { return [] }` convierte un 500 o un error de red en "no tenes
// conversaciones", y la UI no puede distinguir vacio de caido. Con la API
// apagada, el usuario ve un tablero en verde con cero anomalias.

const apiClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  rawStream: vi.fn(),
};

vi.mock('../shared/api/api_client', () => ({
  apiClient,
  parseSseEvent: () => null,
}));

const httpError = (status: number, detail = 'fallo') => {
  const err: any = new Error(detail);
  err.response = { status, data: { detail } };
  return err;
};

let queryService: typeof import('../features/chat/services/query_service').queryService;
let isPredictionQuestion: typeof import('../features/chat/services/query_service').isPredictionQuestion;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  const mod = await import('../features/chat/services/query_service');
  queryService = mod.queryService;
  isPredictionQuestion = mod.isPredictionQuestion;
});

describe('getAnomalies: "0 anomalias" no es lo mismo que "no se pudo preguntar"', () => {
  it('propaga el fallo de red en vez de devolver count 0', async () => {
    apiClient.get.mockRejectedValue(new TypeError('Failed to fetch'));

    // Si esto devolviera `{count: 0}`, el panel pintaria verde y afirmaria que
    // no hay anomalias cuando en realidad nadie pregunto.
    await expect(queryService.getAnomalies()).rejects.toThrow();
  });

  it('propaga el error del servidor con su detalle', async () => {
    apiClient.get.mockRejectedValue(httpError(500, 'Fallo interno'));

    await expect(queryService.getAnomalies()).rejects.toThrow();
  });

  it('rechaza un 200 sin conteo numerico', async () => {
    apiClient.get.mockResolvedValue({ data: { anomalies: [], has_critical: false } });

    await expect(queryService.getAnomalies()).rejects.toThrow(/conteo/i);
  });

  it('devuelve el conteo cuando el servidor si lo manda', async () => {
    const payload = { count: 3, anomalies: [], has_critical: false };
    apiClient.get.mockResolvedValue({ data: payload });

    await expect(queryService.getAnomalies(7)).resolves.toEqual(payload);
    expect(apiClient.get).toHaveBeenCalledWith('/system/anomalies', {
      params: { connection_id: 7 },
    });
  });
});

describe('getThreads y getWidgets: lista vacia no es lo mismo que API caida', () => {
  it('getThreads propaga el fallo', async () => {
    apiClient.get.mockRejectedValue(httpError(500));
    await expect(queryService.getThreads()).rejects.toThrow();
  });

  it('getThreads rechaza una respuesta que no es lista', async () => {
    apiClient.get.mockResolvedValue({ data: { detalle: 'algo raro' } });
    await expect(queryService.getThreads()).rejects.toThrow();
  });

  it('getThreads devuelve la lista cuando el servidor responde bien', async () => {
    const list = [{ id: 'a', title: 'Hilo', connection_id: 1, message_count: 2, updated_at: '' }];
    apiClient.get.mockResolvedValue({ data: list });
    await expect(queryService.getThreads()).resolves.toEqual(list);
  });

  it('getWidgets propaga el fallo en vez de decir "Tablero (0)"', async () => {
    apiClient.get.mockRejectedValue(httpError(500));
    await expect(queryService.getWidgets()).rejects.toThrow();
  });

  it('getWidgets rechaza una respuesta que no es lista', async () => {
    apiClient.get.mockResolvedValue({ data: null });
    await expect(queryService.getWidgets()).rejects.toThrow();
  });
});

describe('borrado: 404 no es lo mismo que borrado confirmado', () => {
  it('devuelve "deleted" cuando el servidor confirma', async () => {
    apiClient.delete.mockResolvedValue({ data: {} });
    await expect(queryService.deleteThread('t1')).resolves.toBe('deleted');
  });

  it('devuelve "already_absent" en 404, que es una respuesta valida', async () => {
    apiClient.delete.mockRejectedValue(httpError(404, 'no existe'));
    await expect(queryService.deleteThread('t1')).resolves.toBe('already_absent');
  });

  it('lanza en cualquier otro status: el hilo sigue existiendo', async () => {
    // Si esto devolviera 'deleted' o 'already_absent', la UI quitaria el hilo de
    // la lista y un reload lo traeria de vuelta.
    apiClient.delete.mockRejectedValue(httpError(500));
    await expect(queryService.deleteThread('t1')).rejects.toThrow();
    apiClient.delete.mockRejectedValue(httpError(401));
    await expect(queryService.deleteThread('t1')).rejects.toThrow();
  });
});

describe('hilo compartido: 404 es null, cualquier otro fallo se propaga', () => {
  it('404 devuelve null', async () => {
    apiClient.get.mockRejectedValue(httpError(404));
    await expect(queryService.getSharedThread('s1')).resolves.toBeNull();
  });

  it('500 no se convierte en null', async () => {
    apiClient.get.mockRejectedValue(httpError(500));
    await expect(queryService.getSharedThread('s1')).rejects.toThrow();
  });
});

describe('sendQuery: un fallo jamas se convierte en un analisis', () => {
  it('propaga el detalle del servidor', async () => {
    apiClient.post.mockRejectedValue(httpError(422, 'payload invalido'));
    await expect(queryService.sendQuery('ventas')).rejects.toThrow(/payload invalido/);
  });

  it('un error de red sin response tambien propaga', async () => {
    apiClient.post.mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(queryService.sendQuery('ventas')).rejects.toThrow();
  });

  it('re-lanza AbortError sin reenvolverlo', async () => {
    const abort: any = new Error('aborted');
    abort.name = 'AbortError';
    apiClient.post.mockRejectedValue(abort);

    // Si se reenvolviera en un Error nuevo, el llamador no podria distinguir
    // "el usuario cancelo" de "el servidor fallo", que son mensajes distintos.
    await expect(queryService.sendQuery('ventas')).rejects.toMatchObject({ name: 'AbortError' });
  });

  it('manda el signal al post para que el abort llegue al fetch', async () => {
    apiClient.post.mockResolvedValue({ data: { question: 'ventas' } });
    const controller = new AbortController();

    await queryService.sendQuery('ventas', 1, undefined, controller.signal);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/chat/query',
      { question: 'ventas', connection_id: 1 },
      { signal: controller.signal }
    );
  });
});

describe('getSuggestions: no inventa capacidades que el servidor no ofrece', () => {
  it('deja la lista vacia ante un fallo, sin inventar preguntas', async () => {
    apiClient.get.mockRejectedValue(httpError(500));
    await expect(queryService.getSuggestions()).resolves.toEqual([]);
  });

  it('devuelve lo que el servidor respondio', async () => {
    apiClient.get.mockResolvedValue({ data: { suggestions: ['A', 'B'] } });
    await expect(queryService.getSuggestions()).resolves.toEqual(['A', 'B']);
  });
});

describe('isPredictionQuestion: el filtro que enruta a /chat/predict', () => {
  it('reconoce las formas explicitas de pedir el futuro', () => {
    expect(isPredictionQuestion('predice el mes que viene')).toBe(true);
    expect(isPredictionQuestion('cuanto facturo')).toBe(true);
    expect(isPredictionQuestion('proyeccion de ingresos')).toBe(true);
  });

  it('no se lleva preguntas que no piden el futuro', () => {
    // "clientes" y "retencion" quedan fuera a proposito: mandarlas al
    // calculo de churn comercial abriria un hueco junto al aislamiento de
    // dominio por rol que el backend hace bien.
    expect(isPredictionQuestion('cuantos clientes tengo')).toBe(false);
    expect(isPredictionQuestion('reporte de retencion de clientes')).toBe(false);
    expect(isPredictionQuestion('ventas totales de enero')).toBe(false);
  });
});