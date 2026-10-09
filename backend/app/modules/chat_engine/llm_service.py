import httpx
import json
import re
import ipaddress
from urllib.parse import urlsplit
from typing import AsyncIterator, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.prompts import PromptManager

# --- SSRF: la validación vive en el SINK, no en el router --------------------
# `generate_completion` acepta `base_url` de cualquier caller. Hoy ningún router
# se lo pasa (los 7 call sites usan `settings`), pero el día que uno lo haga sin
# validar, esta clase haría POST a donde le digan. La allowlist del router
# protects la entrada conocida; acá se cierra la salida.
#
# `LLM_SINK_EXTRA_HOSTS` + `_is_lan_host` existen porque el sink NO puede ser
# más estricto que el despliegue real, o el fix rompe la instalación:
#   - docker-compose.yml:55 pone `OLLAMA_BASE_URL=http://host.docker.internal:11434`
#     por defecto, con `extra_hosts: host.docker.internal:host-gateway`
#     (docker-compose.yml:63). Un backend en contenedor llega al LLM del host por
#     ese nombre, NO por loopback: allowlist de solo loopback = panel de salud
#     roto en Docker, que es donde corre Dat.ia.
#   - un servidor LLM en otra máquina de la LAN (http://192.168.1.50:11434) es
#     un montaje válido de un proyecto local-first.
#
# Lo que NO se acepta es el punto: cualquier otro hostname o IP pública, o sea
# `http://redis-interno:6379`, `http://metadata.google.internal` y el link-local
# 169.254.169.254 de los metadatos de la nube. Tampoco los nombres de servicio
# del compose (`http://ollama:11434`): un hostname arbitrario es exactamente el
# agujero. Si alguien corre Ollama como servicio del compose, que use
# `host.docker.internal` o la IP de la LAN.
LLM_SINK_EXTRA_HOSTS = {"host.docker.internal"}
_LAN_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def _is_lan_host(hostname: str) -> bool:
    """RFC1918 explícito.

    No se usa `ipaddress.is_private` porque devuelve True también para
    169.254.0.0/16 (los metadatos de la nube), que es justo lo que se rechaza.
    """
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return any(ip in net for net in _LAN_NETWORKS)


def validate_llm_base_url(raw: str) -> str:
    """Valida una URL de LLM en el punto donde se emite la request.

    Idempotente con la validación de los routers: si ya pasaron por
    `_resolve_llm_base_url`, esta no cambia nada. Si no pasaron, es la última
    puerta. Devuelve la base usable; levanta ValueError sin tocar la red.
    """
    # Import perezoso: llm_diagnostic_router importa health_service, que importa
    # este modulo, asi que un import a nivel de modulo seria un ciclo.
    from fastapi import HTTPException
    from app.modules.chat_engine.llm_diagnostic_router import (
        LLM_ALLOWED_HOSTS,
        _resolve_llm_base_url,
    )

    url = (raw or "").strip()
    if not url:
        raise ValueError("base_url es obligatorio.")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError(f"base_url invalida: '{raw}'. Debe ser una URL http/https.")
    host = parts.hostname.lower()

    if host in LLM_ALLOWED_HOSTS:
        # Se delega en vez de reimplementar el allowlist de loopback: una sola
        # fuente de verdad, incluido el texto del error.
        try:
            return _resolve_llm_base_url(url)
        except HTTPException as exc:
            raise ValueError(str(exc.detail)) from None

    if host not in LLM_SINK_EXTRA_HOSTS and not _is_lan_host(host):
        raise ValueError(
            f"Host '{parts.hostname}' no permitido. El servidor LLM debe correr en "
            f"local ({', '.join(sorted(LLM_ALLOWED_HOSTS))}), en host.docker.internal "
            "(Docker) o en una IP privada de la red local."
        )
    return url.rstrip('/')


class StreamingThinkFilter:
    """
    Filtro incremental de bloques `<think>` y de escapes ANSI, por stream.

    Por que NO es estado de clase: "estoy dentro de un `<think>`" es estado POR
    PETICION. Con dos usuarios stremeando a la vez, un flag compartido hacia que
    el razonamiento interno de uno se borrara del chat del otro, o al reves, que
    se mostrara. Son instancias separadas: cada `stream_completion` crea la suya.

    `generate_completion` aplica `_clean_thinking_tags` sobre el texto ya
    completo y por eso puede usar regex con DOTALL. Acá cada token llega suelto, y
    un `<think>` partido entre dos chunks no se puede remover con regex. Este
    filtro retiene el fragmento que podria ser el inicio de un tag y lo decide
    cuando llega el resto.

    No reconstruye el texto final: eso lo hace `_clean_thinking_tags` despues,
    sobre el texto acumulado, que es lo que de verdad viaja en la respuesta.
    """

    _ANSI = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    _OPEN = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._in_think = False
        # El resto que quedo sin decidir. ES ESTADO DE INSTANCIA y no local: si
        # fuera local se perderia al terminar cada `feed`, y un `<think>` partido
        # entre dos chunks dejaria pasar el razonamiento interno al chat. Un
        # ejemplo: feed("<thi") + feed("nk>secreto</think>") emitiria "nk>secreto".
        self._pending = ""

    def feed(self, text: str) -> str:
        out = []
        buf = self._pending + text

        while buf:
            if self._in_think:
                end = buf.lower().find(self._CLOSE)
                if end == -1:
                    # El `</think>` de cierre tambien puede venir partido, asi que
                    # se retiene su posible prefijo (el resto ya se sabe que es
                    # razonamiento y se descarta igual).
                    tail = buf[-len(self._CLOSE):].lower()
                    self._pending = tail if tail and self._CLOSE.startswith(tail) else ""
                    return "".join(out)
                buf = buf[end + len(self._CLOSE):]
                self._in_think = False
                continue

            start = buf.lower().find(self._OPEN)
            if start == -1:
                # Retiene un sufijo que podria ser el comienzo de un `<think>`
                # cortado contra el limite del chunk.
                tail = buf[-len(self._OPEN):].lower()
                keep = len(tail) if tail and self._OPEN.startswith(tail) else 0
                out.append(self._ANSI.sub("", buf[:len(buf) - keep]))
                self._pending = buf[len(buf) - keep:]
                return "".join(out)

            out.append(self._ANSI.sub("", buf[:start]))
            buf = buf[start + len(self._OPEN):]
            self._in_think = True

        self._pending = ""
        return "".join(out)


class LLMService:
    """
    Agnostic HTTP client for Local LLM communication.
    Supports llama.cpp / llama.exe serve (http://127.0.0.1:8080),
    Ollama (http://localhost:11434), and OpenAI-compatible local endpoints.
    """

    # Timeout high enough for large models (27B Q4_K_M on CPU can take 60-180s)
    # connect timeout is kept low (2.5s) to fail fast on unresponsive endpoints
    LLM_TIMEOUT = 300.0
    LLM_CONNECT_TIMEOUT = 2.5

    # Parametros de muestreo. No estaban, y esa ausencia era la causa de la
    # corrupcion de salida mas dificil de detectar del pipeline: a temperatura
    # 0.05 un 7B cuantizado (Q4_K_M) entra en bucle de repeticion con facilidad,
    # y un bucle dentro de un JSON de ~1000 tokens produce JSON invalido.
    #
    # `repeat_penalty` corrige el bucle. `seed` hace el SQL reproducible entre
    # corridas, que es lo que permite comparar dos ejecuciones de la MISMA
    # pregunta en el log de auditoria en vez de atribuir la diferencia al modelo.
    # `top_p` recorta la cola improbable sin endurecer la temperatura: a 0.05 ya
    # casi no hay cola, asi que el efecto real es pequeno y no estorba.
    SAMPLING_DEFAULTS: dict = {
        "repeat_penalty": 1.05,
        "top_p": 0.95,
        "seed": 42,
    }

    # `model` resuelto por servidor, cacheado por (base_url, modelo configurado).
    # Es estado de clase y no por peticion a proposito: el modelo cargado no
    # cambia durante la vida del proceso, y descubrirlo otra vez en cada llamada
    # seria un GET extra al servidor por cada pregunta del chat.
    _resolved_models: dict = {}

    @classmethod
    def _clean_thinking_tags(cls, text: str) -> str:
        """Removes <think>...</think> blocks (including unclosed tags) and ANSI escape codes from LLM output."""
        if not text:
            return ""
        # Strip ANSI escape codes (terminal formatting injected by some local models)
        cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        # Strip <think>...</think> reasoning blocks (Qwen3 / DeepSeek R1), including unclosed <think>...
        cleaned = re.sub(r'<think>(?:.*?</think>|.*$)', '', cleaned, flags=re.DOTALL).strip()
        return cleaned if cleaned else text

    @classmethod
    def _get_timeout_config(cls) -> httpx.Timeout:
        """Returns httpx Timeout with fast 2.5s connect timeout and generous read timeout."""
        return httpx.Timeout(timeout=cls.LLM_TIMEOUT, connect=cls.LLM_CONNECT_TIMEOUT)

    @classmethod
    def _as_base_url(cls, url: str) -> str:
        """
        Normalizes a configured server URL down to its BASE.

        `OPENAI_COMPATIBLE_URL` ships as "http://localhost:8000/v1". Composing
        "/v1/chat/completions" onto that produced ".../v1/v1/chat/completions",
        i.e. every inference POSTed the system prompt and the user question to
        Dat.ia's own API (port 8000) and got a 404. Strip the version segment so
        the path is composed exactly once.
        """
        base = (url or "").strip().rstrip('/')
        if base.endswith('/v1'):
            base = base[:-3].rstrip('/')
        return base

    @classmethod
    async def resolve_model_for(cls, base_url: str, configured: str) -> str:
        """Resuelve el `model` contra lo que el servidor de `base_url` tiene.

        Por que hace falta
        -----------------
        El nombre del modelo NO es el mismo en los tres servidores, y el
        configurado suele no ser el de ninguno:

        - Ollama usa tags:      ``qwen2.5-coder:7b``
        - LM Studio usa el id del GGUF:
          ``Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M``

        llama.cpp ignora el campo `model`, pero **LM Studio devuelve 404
        `model_not_found`** ante un nombre que no reconoce. Como `model` se
        mandaba siempre con el valor configurado, ese 404 se repetia en los
        cuatro endpoints de la cadena de fallback y el error final decia "no se
        pudo establecer comunicacion con ningun servidor LLM local" mientras el
        servidor estaba arriba y sano. El sintoma apuntaba al servidor cuando la
        causa era el nombre del modelo.

        Que decide
        ----------
        1. Si el configurado esta entre los que reporta el servidor, se usa: es
           la eleccion explicita del admin y gana.
        2. Si el servidor reporta **exactamente uno** (LM Studio y llama.cpp
           con un solo modelo cargado, que es el caso de Dat.ia), se usa ese.
        3. Si no, o si el servidor no responde, se devuelve el configurado. No
           se adivina entre varios: un `ids[0]` sobre un servidor con cinco
           modelos seria agregar un 404 mas, no quitar uno.

        El resultado se cachea por (base_url, configurado). Un fallo NO se cachea
        por el mismo criterio de `DynamicSchemaPruningService`: "no se pudo
        leer" no es "el servidor no tiene modelos", y cachearlo dejaria al chat
        sin modelo hasta que reiniciara el proceso.
        """
        base = cls._as_base_url(base_url)
        cache_key = f"{base}|{configured}"
        cached = cls._resolved_models.get(cache_key)
        if cached:
            return cached

        resolved = configured
        try:
            async with httpx.AsyncClient(timeout=cls.LLM_CONNECT_TIMEOUT) as client:
                res = await client.get(f"{base}/v1/models")
                if res.status_code == 200:
                    data = res.json()
                    ids = [
                        str(m.get("id"))
                        for m in (data.get("data") or [])
                        if isinstance(m, dict) and m.get("id")
                    ]
                    if configured in ids:
                        resolved = configured
                    elif len(ids) == 1:
                        resolved = ids[0]
                    elif len(ids) > 1 and configured:
                        logger.warning(
                            "El servidor %s reporta %d modelos y ninguno es '%s' (%s). "
                            "Se usa el nombre configurado; si responde 404, ajustalo en Ajustes.",
                            base, len(ids), configured, ", ".join(ids[:5])
                        )
        except Exception as e:
            logger.debug("No se pudo listar modelos en %s: %s", base, e)

        if resolved:
            cls._resolved_models[cache_key] = resolved
        return resolved

    @classmethod
    def _chat_payload(
        cls,
        model: str,
        system_prompt: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> dict:
        """Arma el cuerpo de `/v1/chat/completions`.

        Un solo lugar donde viven los parametros de muestreo. Antes cada uno de
        los tres sitios que arman un payload de chat los repetia, y solo dos de
        los tres payloads llevaban `options`.
        """
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "options": {"num_ctx": settings.LLM_NUM_CTX},
            **cls.SAMPLING_DEFAULTS,
        }
        if stop:
            payload["stop"] = list(stop)
        if stream:
            payload["stream"] = True
        return payload

    @classmethod
    async def generate_completion(
        cls,
        prompt: str,
        system_prompt: str = PromptManager.DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.1,
        max_tokens: int = 300,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Queries the active local LLM server (llama.cpp / Ollama) and returns generated completion.
        Accepts optional dynamic config from request (base_url, model_name) to override settings.

        `stop` corta la generacion en esas cadenas. Lo usa la clasificacion de
        intencion, que pide una sola palabra: sin esto gasta hasta `max_tokens`
        emitiendola y a veces sigue con una frase que ya no se lee.
        """
        effective_model = model_name or settings.OLLAMA_MODEL

        # El `base_url` del caller se valida ACA, en el sink, y no solo en el
        # router: esta clase no tiene por que confiar en quien la invoca, y es lo
        # que impide que el proximo endpoint que pase `base_url` abra la puerta
        # por olvido. Si viene mal, se corta antes de emitir una sola request, en
        # vez de ignorarla en silencio y caer a los defaults (eso seria reportar
        # un resultado que nunca se midio).
        if base_url:
            base_url = validate_llm_base_url(base_url)

        # Cada candidato guarda su base para poder resolverle el `model` contra
        # el servidor que VA a responder: el fallback que gana no es
        # necesariamente el que tiene cargado el modelo configurado.
        candidates = []
        for raw_base in ([base_url] if base_url else []) + [
            "http://127.0.0.1:8080",
            settings.OLLAMA_BASE_URL,
            settings.OPENAI_COMPATIBLE_URL,
        ]:
            cand_base = cls._as_base_url(raw_base)
            candidates.append((cand_base, f"{cand_base}/v1/chat/completions"))

        timeout_cfg = cls._get_timeout_config()

        # Cada intento fallido se anota con su motivo. Antes se registraba con
        # logger.debug, que con el nivel INFO de core/logging.py no llega a
        # ningún lado, así que el único texto que ve el usuario era el mensaje
        # final, que nombraba solo :8080 y :11434 cuando en realidad se probaron
        # :1234, OPENAI_COMPATIBLE_URL y los endpoints nativos.
        failures: List[str] = []

        seen = set()
        for cand_base, url in candidates:
            if url in seen:
                continue
            seen.add(url)

            payload_chat = cls._chat_payload(
                await cls.resolve_model_for(cand_base, effective_model),
                system_prompt, prompt, temperature, max_tokens, stop,
            )

            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    res = await client.post(url, json=payload_chat)
                    if res.status_code == 200:
                        choices = res.json().get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content", "").strip()
                            if text:
                                return cls._clean_thinking_tags(text)
                        failures.append(f"{url} -> 200 sin contenido usable")
                    else:
                        err_body = (res.text or "").lower()
                        if "context size has been exceeded" in err_body or "context size" in err_body or "kv cache" in err_body:
                            logger.error(f"Context size exceeded on {url}: {res.text[:200]}")
                            raise ValueError(f"Context size has been exceeded on LLM server ({url}). Prompt was too long for current slot.")
                        failures.append(f"{url} -> HTTP {res.status_code}: {(res.text or '')[:200]}")
            except ValueError:
                raise
            except Exception as e:
                failures.append(f"{url} -> {type(e).__name__}: {e}")
                logger.debug(f"LLM endpoint {url} no disponible: {str(e)}")

        # Try 2: llama.cpp native completion endpoint (/completion) on 8080
        native_urls = []
        if base_url:
            native_urls.append(f"{cls._as_base_url(base_url)}/completion")
        native_urls.append("http://127.0.0.1:8080/completion")

        for url_native in native_urls:
            try:
                payload_native = {
                    "prompt": f"System: {system_prompt}\nUser: {prompt}\nAssistant:",
                    "temperature": temperature,
                    "n_predict": max_tokens,
                    **cls.SAMPLING_DEFAULTS,
                }
                if stop:
                    payload_native["stop"] = list(stop)
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    res = await client.post(url_native, json=payload_native)
                    if res.status_code == 200:
                        text = res.json().get("content", "").strip()
                        if text:
                            return cls._clean_thinking_tags(text)
                        failures.append(f"{url_native} -> 200 sin contenido")
                    else:
                        err_body = (res.text or "").lower()
                        if "context size has been exceeded" in err_body or "context size" in err_body or "kv cache" in err_body:
                            logger.error(f"Context size exceeded on native {url_native}: {res.text[:200]}")
                            raise ValueError(f"Context size has been exceeded on LLM native server ({url_native}).")
                        failures.append(f"{url_native} -> HTTP {res.status_code}: {(res.text or '')[:200]}")
            except ValueError:
                raise
            except Exception as e:
                failures.append(f"{url_native} -> {type(e).__name__}: {e}")
                logger.debug(f"LLM native endpoint {url_native} no disponible: {str(e)}")

        # Try 3: Ollama /api/generate endpoint on 11434
        ollama_base = base_url if base_url and "11434" in base_url else settings.OLLAMA_BASE_URL
        url_ollama = f"{cls._as_base_url(ollama_base)}/api/generate"
        try:
            ollama_options = {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_NUM_CTX,
                **cls.SAMPLING_DEFAULTS,
            }
            if stop:
                ollama_options["stop"] = list(stop)
            payload_ollama = {
                # `/api/generate` NO acepta un id equivocado en silencio: responde
                # 404 con `model not found`. Se resuelve igual que en la ruta de
                # chat para que el mismo error no se produzca en una y no en la otra.
                "model": await cls.resolve_model_for(cls._as_base_url(ollama_base), effective_model),
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": ollama_options
            }
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                res = await client.post(url_ollama, json=payload_ollama)
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    if text:
                        return cls._clean_thinking_tags(text)
                    failures.append(f"{url_ollama} -> 200 sin contenido")
                else:
                    err_body = (res.text or "").lower()
                    if "context size has been exceeded" in err_body or "context size" in err_body or "kv cache" in err_body:
                        logger.error(f"Context size exceeded on Ollama {url_ollama}: {res.text[:200]}")
                        raise ValueError(f"Context size has been exceeded on Ollama ({url_ollama}).")
                    failures.append(f"{url_ollama} -> HTTP {res.status_code}: {(res.text or '')[:200]}")
        except ValueError:
            raise
        except Exception as e:
            failures.append(f"{url_ollama} -> {type(e).__name__}: {e}")
            logger.debug(f"Ollama endpoint no disponible: {str(e)}")

        detail = " | ".join(failures)
        logger.error("Sin servidor LLM local disponible. Intentos: %s", detail)
        raise Exception(
            "No se pudo establecer comunicación con ningún servidor LLM local. "
            f"Endpoints intentados: {detail}"
        )

    @classmethod
    async def stream_completion(
        cls,
        prompt: str,
        system_prompt: str = PromptManager.DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.1,
        max_tokens: int = 300,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Igual que `generate_completion`, pero emite el texto a medida que el LLM
        lo produce en vez de esperar la respuesta completa.

        Diferencia deliberada con `generate_completion`: NO recorre la cadena de
        endpoints caida. Se queda en el primero que responda con un stream
        parseable. La razon es que un stream a medias no se puede "reintentar y
        seguir": si el primer endpoint corta, el texto parcial ya se emitio y
        pegarlo con el del segundo endpoint seria inventar una respuesta. Si no
        hay ningun endpoint que streemee, este generador no emite NADA y el
        llamador cae al camino no-stream, que es el que hoy funciona.

        Solo se emite texto real del modelo. Este metodo no fabrica progreso:
        si no hay tokens, no hay yield.
        """
        effective_model = model_name or settings.OLLAMA_MODEL

        if base_url:
            base_url = validate_llm_base_url(base_url)

        candidates = []
        for raw_base in ([base_url] if base_url else []) + [
            "http://127.0.0.1:8080",
            settings.OLLAMA_BASE_URL,
            settings.OPENAI_COMPATIBLE_URL,
        ]:
            cand_base = cls._as_base_url(raw_base)
            candidates.append((cand_base, f"{cand_base}/v1/chat/completions"))

        timeout_cfg = cls._get_timeout_config()
        seen = set()
        failures: List[str] = []
        think_filter = StreamingThinkFilter()

        for cand_base, url in candidates:
            if url in seen:
                continue
            seen.add(url)

            # El `model` se resuelve por URL, y aqui importa mas que en la ruta
            # no-stream: si esta mal, LM Studio responde 404 y el stream entero
            # se pierde. `resolve_model_for` esta cacheado, asi que el GET solo
            # ocurre en la primera llamada a cada servidor.
            payload = cls._chat_payload(
                await cls.resolve_model_for(cand_base, effective_model),
                system_prompt, prompt, temperature, max_tokens,
                stream=True,
            )

            emitted = False
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream("POST", url, json=payload) as res:
                        if res.status_code != 200:
                            # El cuerpo de un error hay que leerlo entero: en
                            # streaming no se puede `res.text` sin consumir antes.
                            err_body = (await res.aread()).decode("utf-8", "replace")
                            failures.append(f"{url} -> HTTP {res.status_code}")
                            if "context size" in err_body.lower() or "kv cache" in err_body.lower():
                                raise ValueError(
                                    f"Context size has been exceeded on LLM server ({url})."
                                )
                            continue

                        async for line in res.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            chunk = line[5:].strip()
                            if not chunk or chunk == "[DONE]":
                                if chunk == "[DONE]":
                                    break
                                continue
                            try:
                                delta = json.loads(chunk)
                            except ValueError:
                                continue
                            for choice in delta.get("choices", []) or []:
                                piece = (choice.get("delta") or {}).get("content")
                                if piece:
                                    emitted = True
                                    cleaned = think_filter.feed(piece)
                                    if cleaned:
                                        yield cleaned
                if emitted:
                    return
                failures.append(f"{url} -> 200 sin tokens de contenido")
            except ValueError:
                raise
            except Exception as e:
                failures.append(f"{url} -> {type(e).__name__}: {e}")
                logger.debug(f"LLM stream endpoint {url} no disponible: {str(e)}")

        # Ningun endpoint sirvio un stream. Se levanta para que el llamador use
        # `generate_completion`: es preferible esperar 25 s a mostrar una
        # respuesta inventada.
        logger.warning("Sin stream de LLM disponible. Intentos: %s", " | ".join(failures))
        raise Exception(
            "No se pudo establecer un stream con ningún servidor LLM local. "
            f"Endpoints intentados: {' | '.join(failures)}"
        )
