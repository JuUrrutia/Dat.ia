import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Sustituye los asserts por grep de `scripts/verify_no_faked_success.js`, que
// exigian que el codigo CONTIENERA ciertas cadenas y fallaban ante un refactor
// que preservaba el comportamiento. Aqui se ejecuta el codigo: si el JWT vuelve
// a la URL, el test falla; si el evento no se dispara, el test falla.
//
// No se renderiza React ni se necesita jsdom: `api_client` solo usa `fetch`,
// `localStorage` y `window.dispatchEvent`, y los tres se stubbean.
type FetchCall = { url: string; init: RequestInit };

const stubEnv = () => {
  const store: Record<string, string> = {};
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
  });
  const dispatchEvent = vi.fn();
  vi.stubGlobal('window', { dispatchEvent });
  return { dispatchEvent };
};

const okResponse = (body: unknown = {}) => ({
  ok: true,
  status: 200,
  statusText: 'OK',
  json: async () => body,
  text: async () => JSON.stringify(body),
  blob: async () => body,
});

const errResponse = (status: number, body: unknown) => ({
  ok: false,
  status,
  statusText: 'Error',
  json: async () => body,
  text: async () => JSON.stringify(body),
  blob: async () => body,
});

let calls: FetchCall[] = [];

const loadClient = async () => {
  vi.resetModules();
  return import('../shared/api/api_client');
};

beforeEach(() => {
  calls = [];
  stubEnv();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('api_client: el JWT viaja en la cabecera, nunca en la URL', () => {
  it('manda Authorization y no filtra el token en la query string', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({ ok: true });
    }));

    const { apiClient, setAuthToken } = await loadClient();
    setAuthToken('jwt-secreto-123');

    await apiClient.get('/chat/threads');

    expect(calls).toHaveLength(1);
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer jwt-secreto-123');
    // Un token en la URL queda en los logs del servidor y en el historial del
    // navegador. Esta es la asercion que el grep hacia, aqui sobre la URL real.
    expect(calls[0].url).not.toContain('jwt-secreto-123');
    expect(calls[0].url).not.toMatch(/[?&]token=/);
  });

  it('no manda Authorization cuando no hay sesion', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({});
    }));

    const { apiClient } = await loadClient();
    await apiClient.get('/chat/threads');

    expect((calls[0].init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});

describe('api_client: el signal de aborto llega al fetch', () => {
  it('propaga el AbortSignal al fetch', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({});
    }));

    const { apiClient } = await loadClient();
    const controller = new AbortController();

    await apiClient.post('/chat/query', { question: 'x' }, { signal: controller.signal });

    expect(calls[0].init.signal).toBe(controller.signal);
  });
});

describe('api_client: params que son listas se repiten, no se unen con comas', () => {
  it('serializa cada elemento como su propia clave', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({});
    }));

    const { apiClient } = await loadClient();
    await apiClient.get('/admin/permissions', {
      params: { table_names: ['fact_ventas', 'fact_costos'], role_id: 3 },
    });

    // FastAPI declara `table_names: List[str] = Query(...)` y lee una clave por
    // elemento. `String(['a','b'])` produce "a,b", que el backend tomaria como
    // UN solo nombre de tabla: concede acceso a una tabla que no existe en vez
    // de a las dos. Es un fallo de permisos silencioso, no un error de formato.
    expect(calls[0].url).toContain('table_names=fact_ventas&table_names=fact_costos');
    expect(calls[0].url).not.toContain('fact_ventas%2Cfact_costos');
  });

  it('omite los params que son undefined o null', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({});
    }));

    const { apiClient } = await loadClient();
    await apiClient.get('/x', { params: { a: 1, b: undefined, c: null } });

    expect(calls[0].url).toContain('a=1');
    expect(calls[0].url).not.toContain('b=');
    expect(calls[0].url).not.toContain('c=');
  });
});

describe('api_client: el 403 de cambio de clave pendiente es una instruccion, no un error', () => {
  it('dispara el evento y aun asi propaga el error al consumidor', async () => {
    const { dispatchEvent } = stubEnv();
    vi.stubGlobal('fetch', vi.fn(async () =>
      errResponse(403, { detail: 'Debe cambiar su contrasena en /auth/change-password' })
    ));

    const { apiClient, PASSWORD_CHANGE_PENDING_EVENT } = await loadClient();

    await expect(apiClient.get('/chat/threads')).rejects.toThrow(/change-password/);

    // El evento es lo que abre el formulario forzado. Si el catch se traga el
    // error sin disparar, el usuario ve "error generico" sin salida.
    expect(dispatchEvent).toHaveBeenCalledTimes(1);
    expect(dispatchEvent.mock.calls[0][0].type).toBe(PASSWORD_CHANGE_PENDING_EVENT);
  });

  it('un 403 que no es de clave no dispara el evento', async () => {
    const { dispatchEvent } = stubEnv();
    vi.stubGlobal('fetch', vi.fn(async () => errResponse(403, { detail: 'Sin permisos' })));

    const { apiClient } = await loadClient();
    await expect(apiClient.get('/admin/permissions')).rejects.toThrow();

    expect(dispatchEvent).not.toHaveBeenCalled();
  });
});

describe('api_client: FormData manda su propio Content-Type', () => {
  it('no fuerza application/json sobre un cuerpo multipart', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return okResponse({});
    }));

    const { apiClient } = await loadClient();
    const fd = new FormData();
    fd.append('file', new Blob(['x']), 'base.sqlite');

    await apiClient.post('/connectors/upload', fd);

    // Forzar el Content-Type haria que el navegador no mande el boundary y la
    // subida fallara con un 400 del servidor, no del cliente.
    const headers = calls[0].init.headers as Record<string, string>;
    const contentType =
      headers['Content-Type'] || headers['content-type'];
    expect(contentType).toBeUndefined();
  });
});

describe('api_client: el detail de un 422 llega como string, no como array', () => {
  it('aplana el detail de validacion para que se pueda renderizar', async () => {
    // Este es el body exacto que devuelve FastAPI en un 422 de pydantic. Sin
    // aplanarlo, el catch de connector_service.testConnection lo asignaba a
    // `message` (un array es truthy, asi que su fallback nunca corria) y React
    // lanzaba "Objects are not valid as a React child" al pintarlo, dejando la
    // pagina en negro porque no hay ErrorBoundary.
    vi.stubGlobal('fetch', vi.fn(async () =>
      errResponse(422, {
        detail: [
          { type: 'missing', loc: ['password'], msg: 'Field required', input: {}, url: 'https://errors.pydantic.dev/2.13/v/missing' },
        ],
      })
    ));

    const { apiClient } = await loadClient();

    let caught: any = null;
    try {
      await apiClient.post('/connectors/test', { db_type: 'sqlite', host: 'x', port: 0, database_name: 'd', username: 'admin' });
    } catch (e) {
      caught = e;
    }

    // Es lo que leen los ~29 `err.response?.data?.detail || 'fallback'`.
    expect(Array.isArray(caught.response.data.detail)).toBe(false);
    expect(typeof caught.response.data.detail).toBe('string');
    expect(caught.response.data.detail).toBe('Field required');
    // Y el patron del catch de connector_service, tal cual.
    const shown = caught.response?.data?.detail || 'No se pudo conectar a x:0 (SQLITE).';
    expect(typeof shown).toBe('string');
    expect(caught.message).toBe('Field required');
  });

  it('une varios errores de validacion en un solo string', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      errResponse(422, {
        detail: [
          { type: 'missing', loc: ['password'], msg: 'Field required' },
          { type: 'missing', loc: ['username'], msg: 'Field required' },
        ],
      })
    ));

    const { apiClient } = await loadClient();
    await expect(apiClient.post('/connectors/test', {})).rejects.toThrow('Field required; Field required');
  });

  it('no toca un detail que ya es string de error de dominio', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      errResponse(404, { detail: 'Conexion no encontrada' })
    ));

    const { apiClient } = await loadClient();
    await expect(apiClient.get('/connectors/9')).rejects.toThrow('Conexion no encontrada');
  });
});

describe('parseSseEvent', () => {
  it('devuelve null para los keep-alives que inyectan los proxies', async () => {
    const { parseSseEvent } = await loadClient();
    expect(parseSseEvent(': ping')).toBeNull();
    expect(parseSseEvent('')).toBeNull();
    expect(parseSseEvent('data: sin evento')).toBeNull();
  });

  it('parsea evento y payload', async () => {
    const { parseSseEvent } = await loadClient();
    expect(parseSseEvent('event: delta\ndata: {"text":"hola"}')).toEqual({
      event: 'delta',
      data: { text: 'hola' },
    });
  });

  it('une varias lineas data del mismo evento', async () => {
    const { parseSseEvent } = await loadClient();
    const parsed = parseSseEvent('event: result\ndata: {"a":\ndata: 1}');
    expect(parsed?.data).toEqual({ a: 1 });
  });

  it('un JSON truncado da payload vacio en vez de propagar el error', async () => {
    const { parseSseEvent } = await loadClient();
    expect(parseSseEvent('event: result\ndata: {"a":')).toEqual({
      event: 'result',
      data: {},
    });
  });
});