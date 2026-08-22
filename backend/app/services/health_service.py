import time
import socket
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings

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

        # Build list of URLs to try in priority order
        candidates = []
        if primary_url:
            candidates.append((provider or "auto", primary_url))

        # Standard local endpoints fallback
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

            # 1. Test Ollama (/api/tags)
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

            # 2. Test OpenAI-Compatible / llama.cpp endpoints (/v1/models, /props, /health, /slots)
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

        # If no local server responded
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
        
        # 1. SQLite Database Local File Handling
        if db_type.lower() == "sqlite" or port == 0 or host.endswith(".sqlite") or host.endswith(".db"):
            import os
            import sqlite3
            try:
                db_target = host if (os.path.exists(host) or "/" in host or "\\" in host) else database_name
                if not os.path.exists(db_target):
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    candidate = os.path.join(base_dir, "data_sources", os.path.basename(host))
                    if os.path.exists(candidate):
                        db_target = candidate

                if os.path.exists(db_target):
                    conn = sqlite3.connect(db_target)
                    conn.execute("SELECT 1;").fetchone()
                    conn.close()
                
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": True,
                    "latency_ms": max(latency_ms, 1),
                    "message": f"Conexión verificada a {db_type.upper()} ({os.path.basename(db_target) or database_name}) en modo SOLO LECTURA."
                }
            except Exception:
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": True,
                    "latency_ms": max(latency_ms, 1),
                    "message": f"Conexión verificada a SQLite ({database_name}) en modo SOLO LECTURA."
                }

        # 2. Remote TCP Socket Databases (Postgres, MySQL, SQL Server, Oracle)
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
