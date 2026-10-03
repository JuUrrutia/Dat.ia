/**
 * Guard de regresion para la clase de bug "la UI afirma lo que el servidor no
 * confirmo". Sin framework de tests en el repo (y no se instala uno), esto es un
 * assert script: corre con `node scripts/verify_no_faked_success.js` y falla si
 * vuelve el codigo de dashboard inventado, un fallback que fabrica el conector
 * guardado, o un AbortController que no llega al fetch.
 *
 * Los asserts corren contra el fuente SIN comentarios: varios de estos bugs
 * quedaron documentados en un comentario y un grep ingenuo se auto-disparaba.
 */
const fs = require('fs');
const path = require('path');

const stripComments = (src) =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const read = (rel) => stripComments(fs.readFileSync(path.join(__dirname, '..', rel), 'utf8'));

const queryService = read('src/features/chat/services/query_service.ts');
const connectorService = read('src/features/admin/services/connector_service.ts');
const chatEngine = read('src/features/chat/hooks/useChatEngine.ts');
const adminUsers = read('src/features/admin/hooks/useAdminUsers.ts');
const llmService = read('src/features/chat/services/llm_service.ts');
const chatDashboard = read('src/pages/ChatDashboardPage.tsx');
const chatPromptInput = read('src/components/chat/ChatPromptInput.tsx');
const appRouter = read('src/app/router/AppRouter.tsx');
const permissionService = read('src/features/admin/services/permission_service.ts');
const adminPermissionsHook = read('src/features/admin/hooks/useAdminPermissions.ts');
const adminPermissionsTab = read('src/components/admin/AdminPermissionsTab.tsx');
const adminPage = read('src/pages/AdminPage.tsx');
const authService = read('src/features/auth/services/auth_service.ts');
const userEditModal = read('src/components/admin/UserEditModal.tsx');
const apiClient = read('src/shared/api/api_client.ts');

/**
 * Cuerpo de una funcion, hasta el `}` que la cierra en la misma sangria.
 * Acepta metodos de objeto (`async updateUserRole(...)`) y handlers de hook
 * (`const handleUserSaved = (...) => {`), por eso no exige `async`.
 */
const method = (src, name) => {
  const start = src.search(new RegExp(`(async )?${name}\\s*[(:=]`));
  if (start === -1) throw new Error(`no existe el metodo ${name}`);
  const end = src.indexOf('\n  };', start);
  const endObj = src.indexOf('\n  },', start);
  const stop = [end, endObj].filter((i) => i !== -1).sort((a, b) => a - b)[0];
  return src.slice(start, stop === undefined ? src.length : stop);
};

const checks = [
  // Bug 4: el dashboard con KPIs inventados era inalcanzable (estaba tras un throw).
  ['query_service: sin dashboard de KPIs inventados', !/\$1,029,000|31\.1%|srv-prod-01/.test(queryService)],
  ['query_service: sin validation_status SUCCESS hardcodeado', !/validation_status:\s*'SUCCESS'/.test(queryService)],
  ['query_service: sin import de llm_service', !/from '\.\/llm_service'/.test(queryService)],

  // Bug 5: el AbortController tiene que llegar hasta fetch.
  ['query_service: /chat/query propaga el signal', /apiClient\.post\('\/chat\/query', payload, signal \? \{ signal \}/.test(queryService)],
  ['query_service: el AbortError se propaga sin reenvolver', /err\?\.name === 'AbortError'\) throw err/.test(queryService)],
  ['useChatEngine: manda controller.signal a sendQuery', /controller\.signal,/.test(chatEngine)],

  // Bugs 2 y 3: un conector se crea, cambia y se borra solo si el servidor lo dijo.
  ['connector_service: updateConnector sin catch', !/catch/.test(method(connectorService, 'updateConnector'))],
  ['connector_service: toggleActive sin catch', !/catch/.test(method(connectorService, 'toggleActive'))],
  ['connector_service: deleteConnector sin catch', !/catch/.test(method(connectorService, 'deleteConnector'))],
  ['connector_service: el cache esta namespaciado por usuario', /STORAGE_KEY_PREFIX/.test(connectorService) && !/LEGACY_STORAGE_KEY/.test(connectorService)],

  // Bug 6: borrar hilo tiene que distinguir 404 de borrado confirmado.
  ['query_service: deleteThread distingue 404', /already_absent/.test(method(queryService, 'deleteThread'))],

  // Bug 1: la UI de edicion de rol se elimino porque no habia endpoint. Volvio
  // junto con PATCH /auth/users/{id}, asi que el assert cambia de forma: ya no
  // se puede exigir la ausencia de la capacidad, hay que exigir que la que
  // existe la confirme contra el servidor.
  ['useAdminUsers: el guardado de rol no muta localStorage', !/localStorage/.test(method(adminUsers, 'handleUserSaved'))],
  ['useAdminUsers: el guardado de rol pinta lo que devolvio el servidor', /updatedItem\.role/.test(method(adminUsers, 'handleUserSaved'))],
  ['UserEditModal: el Guardar Rol llama al endpoint, no a localStorage', /authService\.updateUserRole\(/.test(userEditModal) && !/localStorage/.test(userEditModal)],
  ['UserEditModal: el exito se toma del UserOut del servidor', /saved\.role_name/.test(userEditModal)],
  ['UserEditModal: si el server rechaza, no hay exito affirmado', /setSubmitError/.test(userEditModal)],
  ['UserEditModal: el catalogo de roles sale del servidor', /getAvailableRoles\(\)/.test(userEditModal) && !/CORPORATE_ROLES/.test(userEditModal)],
  ['auth_service: expone updateUserRole contra PATCH /auth/users/{id}', /async updateUserRole\(/.test(authService) && /apiClient\.patch<User>\(`\/auth\/users\/\$\{userId\}`/.test(authService)],
  ['api_client: existe el verbo PATCH', /method: 'PATCH'/.test(apiClient)],

  // Bug 9: la lista de modelos es la del servidor, no la configurada.
  ['llm_service: no fabrica available_models', !/models\s*=\s*\[modelName/.test(llmService) && !/available_models:\s*\[modelName/.test(llmService)],
  ['settings: "Probar conexion" no aplica la config detectada', !/setDetectedEndpoint\(\{ url: ep\.url, prov: ep\.prov \}\);\s*\}\s*\}\s*return;/.test(read('src/features/settings/hooks/useSettingsDiagnostics.ts'))],

  // Bonus: getSuggestions no inventa preguntas.
  ['query_service: getSuggestions sin fallback local', !/categor[ií]as de productos|incidentes de TI cr[ií]ticos/.test(queryService)],

  // Bugs 10 y 11: "no pude preguntar" no es "no hay nada".
  ['query_service: getAnomalies propaga el fallo (sin count: 0)', !/catch/.test(method(queryService, 'getAnomalies')) && !/count:\s*0/.test(method(queryService, 'getAnomalies'))],
  ['query_service: getAnomalies no acepta una respuesta sin count numerico', /typeof res\.data\?\.count !== 'number'/.test(method(queryService, 'getAnomalies'))],
  ['query_service: getThreads propaga el fallo (sin catch a [])', !/catch/.test(method(queryService, 'getThreads'))],
  ['query_service: getWidgets propaga el fallo (sin catch a [])', !/catch/.test(method(queryService, 'getWidgets'))],
  ['useChatEngine: el historial distingue cargando / error', /threadsLoaded/.test(chatEngine) && /setThreadsError/.test(chatEngine)],
  ['ChatDashboardPage: el panel de anomalias no arranca en count: 0', !/count:\s*0,\s*anomalies:\s*\[\],\s*has_critical:\s*false\s*\}\);/.test(chatDashboard)],
  ['ChatDashboardPage: el fallo de anomalias se muestra, no se oculta', /Alertas: DESCONOCIDO/.test(chatDashboard)],
];

// Bug 12: con un LLM de 7B en CPU la consulta tarda 8-25 s. La UI mostraba un
// spinner indefinido y, peor, una "fase" que avanzaba por tiempos fijos
// (1400/3200/5500 ms) y decia "Ejecutando consulta en base de datos" a los
// 3,2 s sin saber que estaba pasando: progreso que no mide nada. Ahora hay
// reloj real, aviso de espera larga, cancelacion real, y ninguna barra.
const sendPrompt = method(chatEngine, 'handleSendPrompt');
const cancelPrompt = method(chatEngine, 'handleCancelPrompt');
const chatUi = `${chatDashboard}\n${chatPromptInput}`;

checks.push(
  // 1. Tiempo transcurrido: lo unico que el navegador sabe con certeza.
  ['useChatEngine: mide el tiempo transcurrido con un reloj', /setElapsedSeconds/.test(chatEngine)],
  ['ChatDashboardPage: el tiempo transcurrido se muestra', /\{elapsedSeconds\}s/.test(chatDashboard)],
  ['useChatEngine: el reloj arranca en 0 al enviar', /setElapsedSeconds\(0\)/.test(sendPrompt)],

  // 2. Sin etapas inventadas. El backend no expone ninguna señal de etapa y
  // el frontend no la puede derivar de timings, asi que no se muestra ninguna.
  ['useChatEngine: sin fases de generacion por timers fijos', !/generatingPhase/.test(chatEngine)],
  ['ChatDashboardPage: sin fases de generacion por timers fijos', !/generatingPhase/.test(chatDashboard)],
  ['useChatEngine: sin timers de avance de fase', !/phaseTimer/.test(chatEngine)],
  ['ChatDashboardPage: dice que no conoce la etapa', /no informa en qué etapa/.test(chatDashboard)],

  // 3. Progreso percentual inventado: la clase de bug mas grave aqui, porque un
  // "45%" leido como medicion hace creer al usuario que falta poco cuando puede
  // faltar todo.
  ['Chat UI: sin barra de progreso con porcentaje', !/aria-valuenow|role="progressbar"|progressbar|style=\{\{\s*width/.test(chatUi)],
  ['Chat UI: sin porcentaje de completitud', !/\d\s*%\s*(complet|completad|listo|hecho)|completitud|%\s*completado/i.test(chatUi)],
  ['useChatEngine: sin porcentaje de completitud', !/completitud|%\s*completado|Math\.(round|floor)\([^)]*\*\s*100/.test(chatEngine)],

  // 4. Umbral de espera larga, con el numero justificado en el fuente.
  ['useChatEngine: existe el umbral de espera larga', /LONG_WAIT_NOTICE_SECONDS/.test(chatEngine)],
  // El "por que 8" esta en el comentario del fuente, asi que este assert
  // chequea el valor: si alguien mueve el umbral sin revisar la justificacion
  // del reporte, el numero aqui no vuelve a cuadrar con la UI.
  ['useChatEngine: el umbral de espera larga es 8 s', /LONG_WAIT_NOTICE_SECONDS = 8/.test(chatEngine)],
  ['ChatDashboardPage: el aviso de espera larga se renderiza', /longWaitNotice/.test(chatDashboard)],
  ['ChatDashboardPage: el aviso da el rango real de espera', /8 y 25 segundos/.test(chatDashboard)],
  ['ChatDashboardPage: el aviso dice que no esta colgado', /No est\u00e1 colgado/.test(chatDashboard)],

  // 5. Cancelacion real: aborta, y vuelve la UI a un estado usable.
  ['useChatEngine: existe el handler de cancelar', /abortControllerRef\.current/.test(cancelPrompt) && /controller\.abort\(\)/.test(cancelPrompt)],
  ['useChatEngine: cancelar libera el input y la burbuja de pendiente', /setIsGenerating\(false\)/.test(cancelPrompt) && /setPendingPrompt\(null\)/.test(cancelPrompt)],
  ['ChatDashboardPage: el boton de cancelar esta montado', /onClick=\{handleCancelPrompt\}/.test(chatDashboard) && /aria-label="Cancelar la consulta en curso"/.test(chatDashboard)],
  ['ChatDashboardPage: cancelar no se presenta como "se deshizo"', !/Cancelada sin ejecutar|Se cancel[oó] la ejecuci/.test(chatDashboard)],
  ['useChatEngine: el aviso de cancel es honesto con el servidor', /el motor local puede seguir trabaj/.test(chatEngine)],

  // 6. Timeout: explica, no dice "error".
  ['useChatEngine: el timeout explica que se descarto un resultado real', /pudo seguir trabaj[aá]ndola/.test(chatEngine)],
  ['useChatEngine: el timeout ofrece reintentar', /reintentarl/.test(chatEngine)],
  ['useChatEngine: el timeout no afirma "error"', !/La respuesta tard[oó] demasiado y la solicitud fue cancelada por tiempo de espera/.test(chatEngine)],

  // 7. Fugas de timers. El intervalo vive en un useEffect con cleanup y el
  // unico setTimeout del request se limpia en el finally.
  ['useChatEngine: el setInterval tiene clearInterval en su cleanup', /const ticker = setInterval/.test(chatEngine) && /return \(\) => clearInterval\(ticker\)/.test(chatEngine)],
  ['useChatEngine: hay un unico setInterval', (chatEngine.match(/setInterval/g) || []).length === 1],
  ['useChatEngine: el setTimeout del request se limpia en el finally', /const timeoutId = setTimeout/.test(sendPrompt) && /clearTimeout\(timeoutId\)/.test(sendPrompt)],
  // El `timeoutId` del corte por tiempo se limpia en el `finally`. El segundo
// `setTimeout` que hay en el hook (el volcado del buffer del stream) NO se
// limpia ahi sino en su propio helper y en el cleanup del unmount, asi que el
// conteo dentro de `handleSendPrompt` ya no alcanza como regla: se checkea que
// el timer del stream se cancele en los tres caminos.
['useChatEngine: el timeout del request se limpia en su finally', /clearTimeout\(timeoutId\)/.test(sendPrompt)],
['useChatEngine: el timer de volcado del stream se cancela al descartar', /discardStreamingNarrative[\s\S]{0,400}clearTimeout\(streamFlushTimerRef\.current\)/.test(chatEngine)],
['useChatEngine: el timer de volcado del stream se cancela al desmontar', /useEffect\([\s\S]{0,120}=> \(\) => \{[\s\S]{0,200}clearTimeout\(streamFlushTimerRef\.current\)/.test(chatEngine)],
  ['useChatEngine: handleSendPrompt no crea su propio setInterval', !/setInterval/.test(sendPrompt)],
);

// Bug 13: con un 7B en CPU el motor tarda 8-25 s y la UI no dejaba leer nada
// hasta el final. Ahora hay stream de la narrativa por POST /chat/query/stream.
// Lo que estos asserts protegen es lo que hace que eso sea SEGURO y no una
// segunda forma de mentirle al usuario:
//
//  - `POST /chat/query` sigue existiendo y es el camino de verdad. Si el stream
//    falla, se vuelve ahi y la respuesta llega entera.
//  - Un stream a medias NO se commitea. Lo parcial se muestra en la burbuja de
//    "procesando" y se descarta; al hilo solo entra la respuesta completa.
//  - Sin `result` no hay respuesta: el cliente lanza y reintenta, en vez de
//    devolver lo que leyo a medias como si fuera la respuesta.
const sendQueryStreaming = method(queryService, 'sendQueryStreaming');

checks.push(
  // 1. El camino que hoy funciona no se reemplaza.
  ['query_service: sendQuery (sin stream) sigue existiendo', /async sendQuery\(/.test(queryService)],
  ['useChatEngine: el stream tiene caida a sendQuery', /sendQueryStreaming/.test(sendPrompt) && /sendQuery\(/.test(sendPrompt)],
  ['query_service: sendQueryStreaming pegado al endpoint nuevo', /\/chat\/query\/stream/.test(sendQueryStreaming)],
  ['useChatEngine: el stream se desactiva si falla, no se reintenta siempre', /setStreamingEnabled\(false\)/.test(sendPrompt)],

  // 2. Un stream a medias no deja media respuesta pegada.
  ['query_service: sin evento result no hay respuesta', /!sawResult \|\| !finalResult/.test(sendQueryStreaming)],
  ['query_service: el stream cortado propaga el error, no devuelve parcial', /La respuesta en vivo se cort[oó] a mitad/.test(sendQueryStreaming)],
  // El descarte de lo parcial esta en un helper (`discardStreamingNarrative`)
  // que vacia el estado Y el buffer pendiente: si solo se vaciara el estado,
  // el volcado en vuelo volveria a escribir texto parcial despues del corte.
  ['useChatEngine: existe el descarte de la narrativa parcial', /const discardStreamingNarrative/.test(chatEngine)],
  ['useChatEngine: el descarte limpia estado y buffer pendiente', /discardStreamingNarrative[\s\S]{0,400}streamBufferRef\.current = ''/.test(chatEngine)],
  ['useChatEngine: la narrativa parcial se descarta al terminar', /discardStreamingNarrative\(\)/.test(sendPrompt)],
  ['useChatEngine: la narrativa parcial se descarta al cancelar', /discardStreamingNarrative\(\)/.test(cancelPrompt)],

  // 3. La narrativa stremeada NUNCA se commitea al hilo: el commit usa solo el
  // resultado final que devuelve sendQueryStreaming, que es la QueryResponse
  // completa. Si alguien agrega la narrativa parcial al setThreads, esto falla.
  ['useChatEngine: la narrativa stremeada no entra en setThreads', !/setThreads\([\s\S]{0,400}streamingNarrative/.test(chatEngine)],
  ['useChatEngine: el commit del hilo usa el resultado, no el texto parcial', /results: newResults/.test(sendPrompt)],

  // 4. No se inventa progreso: la UI muestra lo que el modelo ya produjo, y lo
// agrupa en el buffer para no escribir el estado en cada token.
  ['useChatEngine: la narrativa se acumula solo desde el callback del stream', /setStreamingNarrative\(\(prev\) => prev \+ pending\)/.test(chatEngine)],
  ['useChatEngine: el buffer del stream se vacia al volcar', /streamBufferRef\.current = ''/.test(chatEngine)],
  ['ChatDashboardPage: la narrativa en vivo se renderiza', /streamingNarrative/.test(chatDashboard)],

  // 5. El reloj de la parte 1 convive con el stream: el stream lo reemplaza?
  ['useChatEngine: el reloj sigue activo durante el stream', /setElapsedSeconds/.test(sendPrompt)],
  ['ChatDashboardPage: el reloj se sigue mostrando', /\{elapsedSeconds\}s/.test(chatDashboard)],
  ['ChatDashboardPage: la narrativa en vivo no borra el reloj', !/streamingNarrative[\s\S]{0,300}\{elapsedSeconds\}/.test(chatDashboard)],

  // 6. El JWT va en el header, nunca en la query string. Un token en la URL
  // queda en los logs del servidor y en el historial del navegador.
  ['api_client: el stream manda Authorization por header', /rawStream[\s\S]{0,600}Authorization/.test(apiClient)],
  ['api_client: el stream no manda el token en la URL', !/rawStream[\s\S]{0,600}[?&]token=/.test(apiClient)],
  ['query_service: no usa EventSource (no soporta POST ni headers)', !/EventSource/.test(queryService)],
);

// Cambio de contrato: `get_current_user` responde 403 con "cambio de contrasena
// pendiente" en toda ruta salvo /auth/me y /auth/change-password. La UI de cambio
// forzado tiene que existir, ser la unica pantalla disponible, y ese 403 no puede
// quedar como error generico.
const authContext = read('src/features/auth/context/AuthContext.tsx');
const mandatoryModal = read('src/components/auth/MandatoryPasswordChangeModal.tsx');

checks.push(
  // La UI existe y es una RUTA, no un overlay: con el flag activo el dashboard
  // no debe montarse (sus requests mueren en 403). El modal se monta en la ruta
  // /change-password y ProtectedLayout es quien manda alla.
  ['auth: existe la pantalla de cambio de contrasena forzado', /MandatoryPasswordChangeModal/.test(appRouter)],
  ['auth: el guard manda a /change-password con el flag activo', /user\.must_change_password\) \{\s*return <Navigate to="\/change-password" replace \/>/.test(appRouter)],
  ['auth: /change-password es una ruta registrada', /path="\/change-password"/.test(appRouter)],
  ['auth: el dashboard NO se monta con clave pendiente', !/must_change_password\s*&&\s*\(/.test(authContext)],
  ['auth: el modal usa POST /auth/change-password', /authService\.changePassword\(oldPassword, newPassword\)/.test(mandatoryModal)],
  ['auth: al cambiar bien se sigue al destino normal (limpia el flag)', /must_change_password:\s*false/.test(authContext)],
  // Sin esto el overlay z-[100] tapa el logout del Header (z-30): caja sin salida.
  ['auth: el modal forzado tiene salida (logout)', /onCancel/.test(mandatoryModal) && /LogOut/.test(mandatoryModal) && /onCancel=\{logout\}/.test(appRouter)],
  ['auth: el logout del Header queda accesible desde el modal', /z-\[100\]/.test(mandatoryModal) && /z-30/.test(read('src/shared/layout/Header.tsx'))],
  // El 403 se convierte en navegacion al formulario, no en error generico.
  ['api_client: detecta el 403 de cambio pendiente', /isPasswordChangePending/.test(apiClient) && /\/auth\/change-password/.test(apiClient)],
  ['api_client: el 403 dispara el evento en vez de tragarselo', /dispatchEvent\(new CustomEvent\(PASSWORD_CHANGE_PENDING_EVENT\)\)/.test(apiClient)],
  ['api_client: el 403 tambien sigue subiendo al consumidor', /throw error/.test(apiClient)],
  ['auth: escucha el 403 y abre el formulario', /addEventListener\(PASSWORD_CHANGE_PENDING_EVENT/.test(authContext) && /must_change_password:\s*true/.test(authContext)],
  // La exencion del backend: /auth/me y /auth/change-password. Si el frontend
  // no usa /auth/me para restaurar, no puede ni ver el flag.
  ['auth: restaura la sesion contra /auth/me (ruta exenta)', /authService\.getCurrentUser\(\)/.test(authContext)],
  ['auth: el 401 manda a login, el 403 de clave no', /status === 401/.test(authContext) && !/status === 403/.test(authContext)],
);

// Default-deny: los permisos son la unica via de granting. Esta pantalla es la
// que hace usable esa politica; sin ella el admin sube un dataset, todo queda
// bloqueado y el unico camino es curl.
const savePending = method(adminPermissionsHook, 'savePending');
// El catch del PUT: lo que queda despues del `} catch` de savePending.
const savePendingCatch = savePending.split('} catch')[1] || '';
const fetchPermissions = method(adminPermissionsHook, 'fetchPermissions');
const getPermissions = method(permissionService, 'getPermissions');
const setPermissions = method(permissionService, 'setPermissions');

checks.push(
  // 1. La pantalla existe y esta montada en el panel de admin.
  ['permissions: existe el componente de la matriz', /AdminPermissionsTab/.test(adminPermissionsTab)],
  ['permissions: AdminPage importa la pantalla', /AdminPermissionsTab/.test(adminPage)],
  ['permissions: AdminPage tiene una pestana para ella', /setActiveTab\('permissions'\)/.test(adminPage) && /activeTab === 'permissions'/.test(adminPage)],

  // 2. NO se monta para roles no-admin: /permissions es get_current_admin.
  ['permissions: la pantalla va montada detras de un guard de admin', /isAdmin && activeTab === 'permissions'/.test(adminPage)],
  ['permissions: la pestana tambien va tras el guard', /isAdmin && \(\s*<button/.test(adminPage)],
  ['permissions: el guard sale de is_admin del servidor', /const isAdmin = Boolean\(user\?\.is_admin\)/.test(adminPage)],

  // 3. Los roles son los del servidor, no una constante.
  ['permissions: los roles salen de getAvailableRoles()', /authService\.getAvailableRoles\(\)/.test(adminPermissionsHook)],
  ['permissions: sin catalogo de roles hardcodeado', !/CORPORATE_ROLES/.test(adminPermissionsHook) && !/CORPORATE_ROLES/.test(adminPermissionsTab)],
  ['permissions: si /auth/roles falla no hay matriz', /setRoles\(\[\]\)/.test(method(adminPermissionsHook, 'fetchRoles')) && /setRolesError/.test(adminPermissionsHook)],

  // 4. Un fallo al leer NO se presenta como "no hay permisos".
  ['permissions: getPermissions no degrada a []', !/catch/.test(getPermissions)],
  ['permissions: fetchPermissions no degrada la matriz a vacio en silencio', /setPermissionsError/.test(fetchPermissions) && /setPermissions\(\[\]\)/.test(fetchPermissions)],

  // 5. Un fallo del PUT revierte: no puede quedar la casilla pintada como
  //    concedida cuando el servidor no concedio nada.
  ['permissions: savePending descarta el borrador en el catch', /setDraft\(\{\}\)/.test(savePendingCatch)],
  ['permissions: el catch del PUT avisa que no se aplico', /setSaveError/.test(savePendingCatch) && /Ning[uúí]n permiso fue aplicado/.test(savePendingCatch)],
  ['permissions: el exito sale de las filas confirmadas por el servidor', /res\.permissions/.test(savePending) && /Servidor confirm/.test(savePending)],
  ['permissions: no hay setTimeout de "guardado" optimista', !/setTimeout/.test(savePending)],

  // 6. El endpoint real: Query params, no body.
  ['permissions: el PUT usa los Query params del backend', /connection_id: input\.connectionId/.test(setPermissions) && /role_id: input\.roleId/.test(setPermissions) && /table_names: input\.tableNames/.test(setPermissions) && /is_allowed: input\.isAllowed/.test(setPermissions)],
  ['permissions: setPermissions no tiene catch que fabrique exito', !/catch/.test(setPermissions)],
  ['api_client: un array de params se repite, no se une con comas', /Array\.isArray\(v\)/.test(apiClient) && /v\.forEach\(\(item\) => searchParams\.append\(k, String\(item\)\)\)/.test(apiClient)],

  // 7. El caso requires_permission_review es visible, no una lista de casillas
  //    sin marcar.
  ['permissions: la pantalla lee requires_permission_review', /selectedConnector\?\.requires_permission_review/.test(adminPermissionsTab)],
  ['permissions: el aviso dice que las tablas estan bloqueadas', /bloqueadas para todos los roles/.test(adminPermissionsTab) && /sin autorizaci/.test(adminPermissionsTab)],
  ['permissions: bulk grant por rol', /grantAllToRole/.test(adminPermissionsTab) && /Dar todas/.test(adminPermissionsTab)],

  // 8. Ningun hardcodeo de shape que el backend no manda.
  ['permissions: el GET tipa la fila que devuelve list_role_table_permissions', /granted_by_admin: boolean/.test(permissionService) && /role_name: string \| null/.test(permissionService)],
  ['permissions: el PUT tipa la respuesta que arma el router', /permissions: ConfirmedPermission\[\]/.test(permissionService)],
);

let failed = 0;
for (const [name, ok] of checks) {
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
}

console.log(`\n${checks.length - failed}/${checks.length} checks OK`);
process.exit(failed === 0 ? 0 : 1);