"""
Gemini LLM Client — wraps Google Generative AI SDK.

Used by:
  - IntentService.classify_intent()   (system_prompt, user_prompt)
  - IntentService.extract_entities()  (system_prompt, user_prompt)
  - ResponseService.generate_response() (system_prompt, user_prompt)

Public API:
  - generate(system_prompt, user_prompt) → str
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid hard crash if google-generativeai not installed
_genai = None


def _get_genai():
    global _genai
    if _genai is None:
        try:
            import google.generativeai as genai
            _genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai is required. "
                "Install with: pip install google-generativeai"
            )
    return _genai


class GeminiClient:
    """
    Async-friendly Gemini LLM client.

    Usage:
        client = GeminiClient()
        text = await client.generate("You are a parking assistant", "Hello")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._model = None

    def _ensure_model(self):
        """Lazily init the GenerativeModel on first use."""
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

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Send a system + user prompt to Gemini and return the response text.

        The google-generativeai SDK's generate_content_async is truly async.
        """
        model = self._ensure_model()

        # Gemini handles system instruction via the model config or chat
        messages = []
        if system_prompt:
            messages.append({"role": "user", "parts": [system_prompt]})
            messages.append({"role": "model", "parts": ["Đã hiểu. Tôi sẽ tuân theo."]})
        messages.append({"role": "user", "parts": [user_prompt]})

        try:
            response = await model.generate_content_async(
                messages,
                stream=False,
            )

            if not response or not response.text:
                logger.warning("Gemini returned empty response")
                return ""

            return response.text.strip()

        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise

    async def generate_simple(self, prompt: str) -> str:
        """Single-turn prompt without system instruction."""
        return await self.generate(system_prompt="", user_prompt=prompt)
