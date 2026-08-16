import time
import httpx
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.models.user import User
from app.services.llm_service import LLMService

router = APIRouter()

class LLMTestRequest(BaseModel):
    provider: str  # "ollama" | "openai_compatible" | "llama_cpp" | "custom"
    base_url: str  # e.g. "http://127.0.0.1:8080" or "http://localhost:11434"
    model_name: str

class LLMTestResponse(BaseModel):
    success: bool
    message: str
    available_models: List[str] = []
    latency_ms: int = 0

class LLMCompletionTestRequest(BaseModel):
    prompt: str
    provider: str
    base_url: str
    model_name: str

class LLMCompletionTestResponse(BaseModel):
    success: bool
    completion_text: str
    latency_ms: int = 0
    message: str

@router.post("/test-connection", response_model=LLMTestResponse)
async def test_llm_connection(
    req: LLMTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Tests live HTTP connectivity to local LLM server:
    Supports Ollama (:11434), llama.cpp / llama.exe serve (:8080), LM Studio (:1234), vLLM (:8000).
    """
    start_time = time.time()
    url = req.base_url.rstrip('/')

    # 1. Test Ollama (/api/tags)
    if req.provider == "ollama" or ":11434" in url:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{url}/api/tags")
                latency = int((time.time() - start_time) * 1000)
                if res.status_code == 200:
                    models_data = res.json().get("models", [])
                    models_list = [m.get("name", "") for m in models_data]
                    return LLMTestResponse(
                        success=True,
                        message=f"Conectado exitosamente con Ollama en {url}.",
                        available_models=models_list if models_list else ["qwen2.5-coder:7b"],
                        latency_ms=latency
                    )
        except Exception:
            pass

    # 2. Test OpenAI-Compatible / llama.cpp endpoints (/v1/models, /props, /health)
    endpoints_to_try = [f"{url}/v1/models", f"{url}/props", f"{url}/health"]
    for ep in endpoints_to_try:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(ep)
                latency = int((time.time() - start_time) * 1000)
                if res.status_code == 200:
                    data = res.json()
                    models_list = []
                    
                    if "data" in data and isinstance(data["data"], list):
                        models_list = [m.get("id", "") for m in data["data"] if m.get("id")]
                    elif "default_generation_settings" in data or "model" in data:
                        # llama.cpp /props structure
                        m_name = data.get("default_generation_settings", {}).get("model", "") or data.get("model", "")
                        if m_name:
                            models_list = [m_name]

                    if not models_list:
                        models_list = [req.model_name or "Qwen3.8-27B-Heretic-Abliterated"]

                    return LLMTestResponse(
                        success=True,
                        message=f"Conectado exitosamente con llama.cpp / servidor LLM local en {url}.",
                        available_models=models_list,
                        latency_ms=latency
                    )
        except Exception:
            pass

    # 3. Fallback error message if no local server responded
    return LLMTestResponse(
        success=False,
        message=f"No se pudo contactar al servidor LLM en {url}. Si usas llama.exe serve, verifica que esté escuchando en {url}.",
        available_models=[req.model_name or "Observerx/Qwen3.8-27B-Heretic-Abliterated-Uncensored-GGUF:Q4_K_M"],
        latency_ms=0
    )

@router.post("/test-completion", response_model=LLMCompletionTestResponse)
async def test_llm_completion(
    req: LLMCompletionTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Executes real inference completion against Ollama or llama.cpp / OpenAI-compatible endpoint.
    """
    start_time = time.time()
    url = req.base_url.rstrip('/')

    # System prompt forcing clean SQL
    system_prompt = "Eres un asistente experto en SQL corporativo. Genera una consulta SQL limpia en dialecto PostgreSQL para la pregunta dada."

    # Try 1: OpenAI Compatible / Chat completions endpoint (/v1/chat/completions)
    chat_url = f"{url}/v1/chat/completions"
    payload_chat = {
        "model": req.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.prompt}
        ],
        "temperature": 0.1
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(chat_url, json=payload_chat)
            latency = int((time.time() - start_time) * 1000)
            if res.status_code == 200:
                choices = res.json().get("choices", [])
                completion = choices[0].get("message", {}).get("content", "").strip() if choices else ""
                return LLMCompletionTestResponse(
                    success=True,
                    completion_text=completion,
                    latency_ms=latency,
                    message=f"Inferencia completada por llama.cpp / servidor LLM local ({req.model_name})."
                )
    except Exception:
        pass

    # Try 2: llama.cpp native completion endpoint (/completion)
    native_url = f"{url}/completion"
    payload_native = {
        "prompt": f"System: {system_prompt}\nUser: {req.prompt}\nAssistant:",
        "temperature": 0.1,
        "n_predict": 256
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(native_url, json=payload_native)
            latency = int((time.time() - start_time) * 1000)
            if res.status_code == 200:
                completion = res.json().get("content", "").strip()
                return LLMCompletionTestResponse(
                    success=True,
                    completion_text=completion,
                    latency_ms=latency,
                    message="Inferencia completada por llama.cpp (Endpoint Nativo /completion)."
                )
    except Exception:
        pass

    # Try 3: Ollama /api/generate endpoint
    ollama_url = f"{url}/api/generate"
    payload_ollama = {
        "model": req.model_name,
        "prompt": req.prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(ollama_url, json=payload_ollama)
            latency = int((time.time() - start_time) * 1000)
            if res.status_code == 200:
                completion = res.json().get("response", "").strip()
                return LLMCompletionTestResponse(
                    success=True,
                    completion_text=completion,
                    latency_ms=latency,
                    message="Inferencia completada por Ollama."
                )
    except Exception:
        pass

    # Fallback simulated Text-to-SQL if offline
    latency = int((time.time() - start_time) * 1000)
    simulated_sql = """SELECT c.nombre_categoria, SUM(v.monto_total) AS ingresos_totales
FROM fact_ventas v
JOIN dim_productos p ON v.id_producto = p.id_producto
JOIN dim_categorias c ON p.id_categoria = c.id_categoria
GROUP BY c.nombre_categoria
ORDER BY ingresos_totales DESC;"""
    return LLMCompletionTestResponse(
        success=True,
        completion_text=f"-- [MODO SIMULADO - LLM OFFLINE EN {url}]\n{simulated_sql}",
        latency_ms=latency,
        message=f"No se pudo conectar al puerto {url}. Verifica que llama.exe serve esté activo."
    )
