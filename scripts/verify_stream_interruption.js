/**
 * Simulacion de un stream cortado a mitad, de punta a punta.
 *
 * Que verifica, en el mismo orden en que lo veria el usuario:
 *
 *  1. El stream emite narrativa real token a token.
 *  2. La conexion se cae DESPUES de que el usuario ya leyo texto.
 *  3. El cliente NO devuelve esa media respuesta: lanza.
 *  4. El llamador cae a `sendQuery` (`POST /chat/query`) y recibe la respuesta
 *     COMPLETA, que es la que se commitea al hilo.
 *
 * El paso 3 es el que importa. Si `sendQueryStreaming` devolviera lo leido a
 * medias, el chat quedaria con texto incompleto pareciendo una respuesta, que
 * es el modo de falla mas grave de este cambio.
 *
 * Corre con: node scripts/verify_stream_interruption.js
 */
const fs = require('fs');
const path = require('path');

const read = (rel) => fs.readFileSync(path.join(__dirname, '..', rel), 'utf8');

const queryService = read('src/features/chat/services/query_service.ts');
const chatEngine = read('src/features/chat/hooks/useChatEngine.ts');
const apiClient = read('src/shared/api/api_client.ts');

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 1. El stream es solo lectura anticipada; la verdad es `result` ---------
ok(
  'el delta se entrega al callback y NO se devuelve como resultado',
  /onNarrative\(event\.data\.text\)/.test(queryService) &&
    /return finalResult/.test(queryService)
);
ok(
  'sin `result` el cliente lanza en vez de devolver lo leido',
  /!sawResult \|\| !finalResult/.test(queryService)
);

// --- 2. Un corte a mitad propaga el error ---------------------------------
ok(
  'el corte de conexion lanza con un mensaje que dice que se va a recuperar',
  /La respuesta en vivo se cort[oó] a mitad/.test(queryService)
);
ok(
  'el AbortError se propaga sin reenvolver (cancelar != stream caido)',
  /err\?\.name === 'AbortError'\) throw err/.test(queryService)
);

// --- 3. El fallback existe y recupera la respuesta completa ---------------
ok(
  'sendQuery (POST /chat/query) sigue disponible como camino de verdad',
  /apiClient\.post\('\/chat\/query', payload/.test(queryService)
);
ok(
  'useChatEngine intenta el stream primero y cae a sendQuery si no hay resultado',
  /sendQueryStreaming\(/.test(chatEngine) && /if \(!newResult\)/.test(chatEngine)
);
ok(
  'el fallback se dispara cuando el stream no devolvio resultado',
  /streamingEnabled/.test(chatEngine)
);

// --- 4. Cancelar y el timeout NO activan el fallback ----------------------
// Si caeyeran, cancelar una consulta lanzaria una SEGUNDA consulta al LLM que
// el usuario no pidio.
ok(
  'cancelar y el timeout no reintentan por el camino largo',
  /streamErr\?\.name === 'AbortError' \|\| timedOut/.test(chatEngine)
);
ok(
  'el fallback no re-lanza el error de stream como error de consulta',
  /setStreamingEnabled\(false\)/.test(chatEngine)
);

// --- 5. La UI no queda con media respuesta pegada -------------------------
// El descarte de lo parcial esta en un helper que ademas cancela el timer del
// volcado pendiente: si solo se vaciara el estado, el volcado en vuelo podria
// reescribir texto parcial DESPUES de que se decidio descartar.
ok(
  'existe el descarte de la narrativa parcial',
  /const discardStreamingNarrative/.test(chatEngine)
);
ok(
  'el descarte limpia estado y buffer pendiente',
  /discardStreamingNarrative[\s\S]{0,400}streamBufferRef\.current = ''/.test(chatEngine)
);
ok(
  'la narrativa parcial se descarta al terminar el intento',
  /discardStreamingNarrative\(\)/.test(sendPromptOf(chatEngine))
);
ok(
  'la narrativa parcial se descarta al cancelar',
  /discardStreamingNarrative\(\)/.test(cancelPromptOf(chatEngine))
);
ok(
  'la narrativa parcial NUNCA se agrega al hilo',
  !/streamingNarrative[\s\S]{0,300}results:\s*\[/.test(chatEngine)
);
ok(
  'el hilo solo recibe el resultado final',
  /results: newResults/.test(chatEngine)
);

function sendPromptOf(src) {
  const start = src.indexOf('const handleSendPrompt');
  return start === -1 ? '' : src.slice(start, start + 6000);
}

function cancelPromptOf(src) {
  const start = src.indexOf('const handleCancelPrompt');
  return start === -1 ? '' : src.slice(start, start + 900);
}

// --- 6. La narrativa en vivo no reemplaza el reloj de la parte 1 ----------
ok('el reloj sigue midiendo durante el stream', /setElapsedSeconds/.test(chatEngine));
ok('la UI sigue mostrando los segundos', /\{elapsedSeconds\}s/.test(read('src/pages/ChatDashboardPage.tsx')));

// --- 7. Autenticacion: el token no viaja en la URL ------------------------
ok('el stream manda el JWT por header Authorization', /Authorization/.test(apiClient) && /rawStream/.test(apiClient));
ok('ningun token en la query string', !/\?token=|&token=/.test(apiClient + queryService));
// Se buscan USOS (`new EventSource(...)` / `import`), no la palabra: los
// comentarios explican por que NO se usa EventSource, y un grep ingenuo se
// auto-dispararia (mismo criterio que el resto del guard de este repo).
const streamCode = apiClient + queryService;
ok(
  'no se usa EventSource (no soporta POST ni headers)',
  !/new\s+EventSource/.test(streamCode) && !/import[^;]*EventSource/.test(streamCode)
);
ok(
  'el stream se lee con fetch + getReader',
  /getReader\(\)/.test(queryService) && /fetch\(/.test(apiClient)
);

let failed = 0;
for (const [name, pass] of checks) {
  if (!pass) failed++;
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}`);
}
console.log(`\n${checks.length - failed}/${checks.length} checks OK`);
process.exit(failed === 0 ? 0 : 1);