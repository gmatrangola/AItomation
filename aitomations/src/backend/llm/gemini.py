# aitomations/src/backend/llm/gemini.py
import logging
from collections.abc import Iterator
from typing import Any

import google.generativeai as genai

from .base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """Generate text using Gemini (non-streaming)."""
        api_key = options.get("gemini_api_key")
        model_name = options.get("gemini_model", "gemini-1.5-flash")

        if not api_key:
            raise ValueError("Gemini API key not configured.")

        genai.configure(api_key=api_key)
        logger.info(f"Calling Gemini with model {model_name}")

        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        full_response_text = response.text

        return {
            "full_response": full_response_text,
            "model": model_name,
            "provider": "gemini",
        }

    def generate_stream(self, prompt: str, options: dict[str, Any]) -> Iterator[str]:
        """Generate text using Gemini with streaming."""
        api_key = options.get("gemini_api_key")
        model_name = options.get("gemini_model", "gemini-1.5-flash")

        if not api_key:
            raise ValueError("Gemini API key not configured.")

        genai.configure(api_key=api_key)
        logger.info(f"Streaming from Gemini with model {model_name}")

        model = genai.GenerativeModel(model_name)

        try:
            response = model.generate_content(prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

            logger.info("Gemini streaming complete")

        except Exception as e:
            error_msg = f"❌ Gemini streaming error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
