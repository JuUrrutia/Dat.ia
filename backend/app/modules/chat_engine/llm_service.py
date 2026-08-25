import httpx
import re
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.core.prompts import PromptManager

class LLMService:
    """
    Agnostic HTTP client for Local LLM communication.
    Supports llama.cpp / llama.exe serve (http://127.0.0.1:8080),
    Ollama (http://localhost:11434), and OpenAI-compatible local endpoints.
    """

    DEFAULT_ENDPOINTS = [
        "http://127.0.0.1:8080",
        "http://localhost:11434",
        "http://localhost:1234"
    ]

    # Timeout high enough for large models (27B Q4_K_M on CPU can take 60-180s)
    # connect timeout is kept low (2.5s) to fail fast on unresponsive endpoints
    LLM_TIMEOUT = 300.0
    LLM_CONNECT_TIMEOUT = 2.5

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
    async def generate_completion(
        cls,
        prompt: str,
        system_prompt: str = PromptManager.DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.1,
        max_tokens: int = 300,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> str:
        """
        Queries the active local LLM server (llama.cpp / Ollama) and returns generated completion.
        Accepts optional dynamic config from request (base_url, model_name) to override settings.
        """
        effective_model = model_name or settings.OLLAMA_MODEL

        # Build list of URLs to try based on provided config or defaults
        urls_to_try = []
        if base_url:
            urls_to_try.append(f"{base_url.rstrip('/')}/v1/chat/completions")
        urls_to_try.extend([
            "http://127.0.0.1:8080/v1/chat/completions",
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions",
            f"{settings.OPENAI_COMPATIBLE_URL.rstrip('/')}/v1/chat/completions"
        ])
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for u in urls_to_try:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)

        payload_chat = {
            "model": effective_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "options": {"num_ctx": 16384}
        }

        timeout_cfg = cls._get_timeout_config()

        for url in unique_urls:
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    res = await client.post(url, json=payload_chat)
                    if res.status_code == 200:
                        choices = res.json().get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content", "").strip()
                            if text:
                                return cls._clean_thinking_tags(text)
            except Exception as e:
                logger.debug(f"LLM endpoint {url} no disponible: {str(e)}")

        # Try 2: llama.cpp native completion endpoint (/completion) on 8080
        native_urls = []
        if base_url:
            native_urls.append(f"{base_url.rstrip('/')}/completion")
        native_urls.append("http://127.0.0.1:8080/completion")

        for url_native in native_urls:
            try:
                payload_native = {
                    "prompt": f"System: {system_prompt}\nUser: {prompt}\nAssistant:",
                    "temperature": temperature,
                    "n_predict": max_tokens
                }
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    res = await client.post(url_native, json=payload_native)
                    if res.status_code == 200:
                        text = res.json().get("content", "").strip()
                        if text:
                            return cls._clean_thinking_tags(text)
            except Exception as e:
                logger.debug(f"LLM native endpoint {url_native} no disponible: {str(e)}")

        # Try 3: Ollama /api/generate endpoint on 11434
        ollama_base = base_url if base_url and "11434" in base_url else settings.OLLAMA_BASE_URL
        try:
            url_ollama = f"{ollama_base.rstrip('/')}/api/generate"
            payload_ollama = {
                "model": effective_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 16384}
            }
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                res = await client.post(url_ollama, json=payload_ollama)
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    if text:
                        return cls._clean_thinking_tags(text)
        except Exception as e:
            logger.debug(f"Ollama endpoint no disponible: {str(e)}")

        raise Exception("No se pudo establecer comunicación con ningún servidor LLM local (llama.cpp en :8080 u Ollama en :11434).")
