# aitomations/src/backend/llm/gemini.py
import logging
from collections.abc import Iterator
from typing import Any

import google.generativeai as genai

from api.errors import APIError, ErrorCode

from .base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """Generate text using Gemini (non-streaming)."""
        api_key = options.get("gemini_api_key")
        model_name = options.get("gemini_model", "gemini-1.5-flash")

        if not api_key:
            raise APIError(ErrorCode.INVALID_API_KEY, {"provider": "gemini"})

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)

            return {
                "full_response": response.text,
                "model": model_name,
                "provider": "gemini",
            }

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise APIError(
                ErrorCode.LLM_ERROR,
                {"provider": "gemini", "model": model_name, "details": str(e)},
            ) from e

    def generate_stream(self, prompt: str, options: dict[str, Any]) -> Iterator[str]:
        """Generate text using Gemini with streaming."""
        api_key = options.get("gemini_api_key")
        model_name = options.get("gemini_model", "gemini-1.5-flash")

        if not api_key:
            raise APIError(ErrorCode.INVALID_API_KEY, {"provider": "gemini"})

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise APIError(
                ErrorCode.LLM_ERROR,
                {"provider": "gemini", "model": model_name, "details": str(e)},
            ) from e
