import time
import httpx
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.models.user import User
from app.services.llm_service import LLMService
from app.core.config import settings
from app.core.prompts import PromptManager

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

from app.services.health_service import HealthService

@router.post("/test-connection", response_model=LLMTestResponse)
async def test_llm_connection(
    req: LLMTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Tests live HTTP connectivity to local LLM server:
    Supports Ollama (:11434), llama.cpp / llama.exe serve (:8080), LM Studio (:1234), vLLM (:8000).
    """
    result = await HealthService.check_llm_connectivity(
        provider=req.provider,
        base_url=req.base_url,
        model_name=req.model_name,
        timeout=3.0
    )
    return LLMTestResponse(
        success=result["success"],
        message=result["message"],
        available_models=result.get("available_models", [req.model_name or settings.OLLAMA_MODEL]),
        latency_ms=result.get("latency_ms", 0)
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
    system_prompt = PromptManager.SQL_TEST_SYSTEM_PROMPT

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

    latency = int((time.time() - start_time) * 1000)
    return LLMCompletionTestResponse(
        success=False,
        completion_text="",
        latency_ms=latency,
        message=f"IA local no disponible. Conecte Ollama/llama.cpp en {url} para ejecutar consultas."
    )
