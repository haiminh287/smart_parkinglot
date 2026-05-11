"""
LLM Client — hỗ trợ 2 backend:

1. **OpenAI-compatible** (default nếu `LLM_BASE_URL` set) — gọi qua httpx tới
   endpoint tuỳ chỉnh, vd local proxy `http://host.docker.internal:8045/v1`.
2. **Google Gemini native** (fallback) — dùng google-generativeai SDK khi không
   có LLM_BASE_URL, cần `GEMINI_API_KEY`.

Giữ class name `GeminiClient` để `main.py` không phải sửa.

Public API:
  - generate(system_prompt, user_prompt) → str
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_genai = None


def _get_genai():
    global _genai
    if _genai is None:
        try:
            import google.generativeai as genai
            _genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai required when LLM_BASE_URL is not set"
            )
    return _genai


class GeminiClient:
    """LLM client — auto switch giữa OpenAI-compat proxy và Gemini SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # Ưu tiên LLM_BASE_URL (OpenAI-compat endpoint) nếu có
        self.base_url = (base_url or getattr(settings, "LLM_BASE_URL", "") or "").rstrip("/")
        self.api_key = (
            api_key
            or getattr(settings, "LLM_API_KEY", "")
            or settings.GEMINI_API_KEY
        )
        self.model_name = (
            model_name
            or getattr(settings, "LLM_MODEL", "")
            or settings.GEMINI_MODEL
        )
        self._model = None  # Gemini SDK model instance (lazy)
        self._use_openai = bool(self.base_url)
        if self._use_openai:
            logger.info(
                "LLM client: OpenAI-compat at %s model=%s", self.base_url, self.model_name,
            )
        else:
            logger.info("LLM client: Google Gemini SDK model=%s", self.model_name)

    def _ensure_gemini_model(self):
        if self._model is None:
            genai = _get_genai()
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_output_tokens": 1024,
                },
            )
        return self._model

    async def _generate_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Gọi OpenAI-compat endpoint (/chat/completions)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 1024,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(
                    "OpenAI-compat LLM %s → HTTP %s: %s",
                    self.base_url, resp.status_code, resp.text[:300],
                )
                raise RuntimeError(f"LLM HTTP {resp.status_code}")
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                logger.warning("LLM returned no choices: %s", str(data)[:200])
                return ""
            return (choices[0].get("message") or {}).get("content", "").strip()

    async def _generate_gemini(self, system_prompt: str, user_prompt: str) -> str:
        model = self._ensure_gemini_model()
        messages = []
        if system_prompt:
            messages.append({"role": "user", "parts": [system_prompt]})
            messages.append({"role": "model", "parts": ["Đã hiểu. Tôi sẽ tuân theo."]})
        messages.append({"role": "user", "parts": [user_prompt]})
        response = await model.generate_content_async(messages, stream=False)
        if not response or not response.text:
            logger.warning("Gemini returned empty response")
            return ""
        return response.text.strip()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        try:
            if self._use_openai:
                return await self._generate_openai(system_prompt, user_prompt)
            return await self._generate_gemini(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"LLM error: {e}", exc_info=True)
            raise

    async def generate_simple(self, prompt: str) -> str:
        return await self.generate(system_prompt="", user_prompt=prompt)
