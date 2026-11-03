import time
import socket
import asyncio
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from urllib.parse import urlsplit


async def _port_open(url: str, timeout: float) -> bool:
    """El puerto de `url` acepta conexiones TCP.

    Distingue "nadie escucha" de "escucha pero no me Sirve". Un `httpx` con
    timeout se come los 2 s completos contra un puerto cerrado, mientras que el
    probe TCP falla en milisegundos. La diferencia importa cuando se prueban 30
    combinaciones host/puerto: contra un puerto muerto pasabamos de 61 s.

    `to_thread` porque `socket.create_connection` es bloqueante y esto corre
    dentro de un `async def`.
    """
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        # Techo propio y corto: contra loopback, un puerto vivo acepta el SYN en
        # microsegundos. Un puerto muerto se queda esperando el paquete descartado
        # del firewall hasta el timeout, asi que 2 s por candidato son 12 s solo de
        # dead-probing. 250 ms no le da tiempo a un servidor lento de arrancar y
        # devuelve la respuesta en el acto.
        probe_timeout = min(timeout, 0.25)
        sock = await asyncio.to_thread(socket.create_connection, (parts.hostname, port), probe_timeout)
        sock.close()
        return True
    except Exception:
        return False


class HealthService:
    """
    Centralized health & connectivity check service for local LLM engines and corporate databases.
    Prevents logic duplication across administration and system monitoring endpoints.
    """

    @classmethod
    async def check_llm_connectivity(
        cls,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Tests live HTTP connectivity to local LLM server:
        Supports Ollama (:11434), llama.cpp / llama.exe serve (:8080), LM Studio (:1234), vLLM (:8000).
        Automatically probes active local ports if the configured one fails.
        """
        start_time = time.time()
        primary_url = (base_url or "").rstrip('/')
        default_model = model_name or settings.OLLAMA_MODEL

        # El `base_url` se valida ACA, en el sink, y no solo en el router: los
        # routers validan la entrada conocida, pero esta clase emite httpx GET a
        # donde le digan y no tiene por que confiar en quien la llame (por
        # ejemplo system/router.py:51 le pasa settings.OLLAMA_BASE_URL, que en
        # Docker es http://host.docker.internal:11434 y debe seguir valiendo).
        # Idempotente con la validación del router: si ya pasó, no cambia nada.
        # Un base_url rechazado no se probea ni se reporta como activo: se
        # devuelve success:False con el motivo, sin afirmar nada sobre el LLM.
        if base_url:
            try:
                from app.modules.chat_engine.llm_service import validate_llm_base_url
                primary_url = validate_llm_base_url(base_url)
            except ValueError as exc:
                return {
                    "success": False,
                    "latency_ms": 0,
                    "message": f"No se pudo verificar el servidor LLM: {exc}",
                    "available_models": [],
                    "active_url": "",
                    "provider": provider or "ollama",
                }

        candidates = []
        if primary_url:
            candidates.append((provider or "auto", primary_url))

        fallbacks = [
            ("llama_cpp", "http://127.0.0.1:8080"),
            ("llama_cpp", "http://localhost:8080"),
            ("ollama", "http://localhost:11434"),
            ("ollama", "http://127.0.0.1:11434"),
            ("openai_compatible", "http://localhost:1234"),
            ("openai_compatible", "http://127.0.0.1:1234"),
        ]

        seen_urls = set()
        if primary_url:
            seen_urls.add(primary_url)

        for p, u in fallbacks:
            if u not in seen_urls:
                seen_urls.add(u)
                candidates.append((p, u))

        for cand_provider, cand_url in candidates:
            cand_start = time.time()

            # Un puerto cerrado no merece cinco intentos HTTP. En Windows el
            # firewall descarta los paquetes en vez de rechazar el loopback, asi
            # que cada GET a un puerto sin escuchar se come el timeout COMPLETO
            # en vez de fallar al instante. Medido: 6 candidatos x 5 endpoints x
            # 2 s = 61 s de chequeo con el LLM apagado, y era la causa de que 6
            # tests de la suite tardaran 38-61 s cada uno.
            # El probe TCP decide en una llamada y es el mismo criterio que ya
            # aplica `check_postgres_connection` mas abajo en este archivo.
            if not await _port_open(cand_url, timeout):
                continue

            if cand_provider == "ollama" or ":11434" in cand_url or cand_provider == "auto":
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        res = await client.get(f"{cand_url}/api/tags")
                        if res.status_code == 200:
                            latency = max(int((time.time() - cand_start) * 1000), 1)
                            models_data = res.json().get("models", [])
                            models_list = [m.get("name", "") for m in models_data if m.get("name")]
                            return {
                                "success": True,
                                "latency_ms": latency,
                                "message": f"Conectado exitosamente con Ollama en {cand_url}.",
                                "available_models": models_list if models_list else [default_model],
                                "active_url": cand_url,
                                "provider": "ollama"
                            }
                except Exception:
                    pass

            endpoints_to_try = [f"{cand_url}/v1/models", f"{cand_url}/props", f"{cand_url}/health", f"{cand_url}/slots"]
            for ep in endpoints_to_try:
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        res = await client.get(ep)
                        if res.status_code == 200:
                            latency = max(int((time.time() - cand_start) * 1000), 1)
                            models_list = []
                            try:
                                data = res.json()
                                if isinstance(data, dict):
                                    if "data" in data and isinstance(data["data"], list):
                                        models_list = [m.get("id", "") for m in data["data"] if m.get("id")]
                                    elif "default_generation_settings" in data or "model" in data:
                                        m_name = data.get("default_generation_settings", {}).get("model", "") or data.get("model", "")
                                        if m_name:
                                            models_list = [m_name]
                            except Exception:
                                pass

                            if not models_list:
                                models_list = [default_model]

                            detected_prov = "llama_cpp" if (":8080" in cand_url or "/props" in ep or "/slots" in ep) else "openai_compatible"
                            prov_name = "llama.cpp / llama-server" if detected_prov == "llama_cpp" else "servidor LLM local"

                            return {
                                "success": True,
                                "latency_ms": latency,
                                "message": f"Conectado exitosamente con {prov_name} en {cand_url}.",
                                "available_models": models_list,
                                "active_url": cand_url,
                                "provider": detected_prov
                            }
                except Exception:
                    pass

        display_url = primary_url or settings.OLLAMA_BASE_URL
        return {
            "success": False,
            "latency_ms": 0,
            "message": f"No se pudo contactar al servidor LLM local ({display_url} ni puertos 8080/11434/1234). Verifica que llama.exe serve u Ollama esté activo.",
            "available_models": [default_model],
            "active_url": display_url,
            "provider": provider or "ollama"
        }

    @classmethod
    def check_db_connectivity(
        cls,
        host: str,
        port: int,
        timeout: float = 3.0,
        db_type: str = "BD",
        database_name: str = ""
    ) -> Dict[str, Any]:
        """
        Tests real network TCP socket connectivity or local SQLite file readiness.
        """
        start_time = time.time()
        
        if db_type.lower() == "sqlite" or port == 0 or host.endswith(".sqlite") or host.endswith(".db"):
            import os
            import sqlite3
            try:
                db_target = host if (os.path.exists(host) or "/" in host or "\\" in host) else database_name
                if not os.path.exists(db_target):
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    candidate = os.path.join(base_dir, "data_sources", os.path.basename(host))
                    if os.path.exists(candidate):
                        db_target = candidate

                if not os.path.exists(db_target):
                    # Antes el `if` no tenia else: si el fichero no existia en ninguna
                    # ruta candidata se saltaba el bloque entero y caia al `return`
                    # de abajo con success=True. Es decir, reportaba como verificada
                    # una conexion a un fichero inexistente, y `except` tambien
                    # devolvia True. El panel de salud miente y, como alimentaba
                    # `global_status`, un conector caido dejaba el sistema en
                    # OPERATIVO y sin emitir la anomalia `conn-offline`.
                    return {
                        "success": False,
                        "latency_ms": max(int((time.time() - start_time) * 1000), 1),
                        "message": f"No se encontro el fichero SQLite en {db_target}.",
                    }

                conn = sqlite3.connect(f"file:{os.path.abspath(db_target)}?mode=ro", uri=True)
                try:
                    conn.execute("SELECT 1;").fetchone()
                finally:
                    conn.close()
                
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": True,
                    "latency_ms": max(latency_ms, 1),
                    "message": f"Conexión verificada a {db_type.upper()} ({os.path.basename(db_target) or database_name}) en modo SOLO LECTURA."
                }
            except Exception as exc:
                # Tambien decia "verificada" cuando la apertura fallaba por
                # permisos, corrupcion o error de disco.
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": False,
                    "latency_ms": max(latency_ms, 1),
                    "message": f"No se pudo verificar la conexión a SQLite ({database_name}): {exc}"
                }

        try:
            sock = socket.create_connection((host, int(port)), timeout=timeout)
            sock.close()
            latency_ms = int((time.time() - start_time) * 1000)
            db_label = f" ({host}/{database_name})" if database_name else f" ({host}:{port})"
            return {
                "success": True,
                "latency_ms": latency_ms,
                "message": f"Conexión exitosa al puerto {port} de {db_type.upper()}{db_label} en modo SOLO LECTURA."
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": 0,
                "message": f"No se pudo conectar a {host}:{port} ({db_type.upper()}) - {str(e)}"
            }
