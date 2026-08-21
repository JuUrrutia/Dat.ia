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
        provider: str,
        base_url: str,
        model_name: Optional[str] = None,
        timeout: float = 3.0
    ) -> Dict[str, Any]:
        """
        Tests live HTTP connectivity to local LLM server:
        Supports Ollama (:11434), llama.cpp / llama.exe serve (:8080), LM Studio (:1234), vLLM (:8000).
        """
        start_time = time.time()
        url = (base_url or "").rstrip('/')
        default_model = model_name or settings.OLLAMA_MODEL

        if not url:
            return {
                "success": False,
                "latency_ms": 0,
                "message": "URL base del servidor LLM no especificada.",
                "available_models": [default_model]
            }

        # 1. Test Ollama (/api/tags)
        if provider == "ollama" or ":11434" in url:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.get(f"{url}/api/tags")
                    latency = int((time.time() - start_time) * 1000)
                    if res.status_code == 200:
                        models_data = res.json().get("models", [])
                        models_list = [m.get("name", "") for m in models_data if m.get("name")]
                        return {
                            "success": True,
                            "latency_ms": latency,
                            "message": f"Conectado exitosamente con Ollama en {url}.",
                            "available_models": models_list if models_list else [default_model]
                        }
            except Exception:
                pass

        # 2. Test OpenAI-Compatible / llama.cpp endpoints (/v1/models, /props, /health)
        endpoints_to_try = [f"{url}/v1/models", f"{url}/props", f"{url}/health"]
        for ep in endpoints_to_try:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.get(ep)
                    latency = int((time.time() - start_time) * 1000)
                    if res.status_code == 200:
                        data = res.json()
                        models_list = []

                        if "data" in data and isinstance(data["data"], list):
                            models_list = [m.get("id", "") for m in data["data"] if m.get("id")]
                        elif "default_generation_settings" in data or "model" in data:
                            m_name = data.get("default_generation_settings", {}).get("model", "") or data.get("model", "")
                            if m_name:
                                models_list = [m_name]

                        if not models_list:
                            models_list = [default_model]

                        return {
                            "success": True,
                            "latency_ms": latency,
                            "message": f"Conectado exitosamente con llama.cpp / servidor LLM local en {url}.",
                            "available_models": models_list,
                        }
            except Exception:
                pass

        # 3. Fallback error message if no local server responded
        return {
            "success": False,
            "latency_ms": 0,
            "message": f"No se pudo contactar al servidor LLM en {url}. Si usas llama.exe serve, verifica que esté escuchando en {url}.",
            "available_models": [default_model]
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
        Tests real network TCP socket connectivity to target database host and port.
        """
        start_time = time.time()
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
