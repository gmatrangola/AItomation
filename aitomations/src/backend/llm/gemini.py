# aitomations/src/backend/llm/gemini.py
import logging
from collections.abc import Iterator
from typing import Any

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from api.errors import APIError, ErrorCode

from .base import LLMProvider

logger = logging.getLogger(__name__)

_SAFETY_FINISH_REASON = 3  # FinishReason.SAFETY in the google.generativeai protobuf enum

# Home automation prompts legitimately mention alarms, locks, gas sensors, etc.
# BLOCK_ONLY_HIGH prevents false positives while still blocking genuinely harmful content.
_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


def _safe_chunk_text(chunk: Any) -> str | None:
    """Return chunk text, None if the chunk has no content, or raise APIError on safety block."""
    candidates = getattr(chunk, "candidates", None)
    if candidates and candidates[0].finish_reason == _SAFETY_FINISH_REASON:
        ratings = {r.category.name: r.probability.name for r in candidates[0].safety_ratings}
        logger.warning(f"Gemini response blocked by safety filters: {ratings}")
        raise APIError(
            ErrorCode.LLM_ERROR,
            {
                "provider": "gemini",
                "details": "Response blocked by Gemini safety filters. Try rephrasing your request.",
            },
        )
    try:
        return chunk.text or None
    except ValueError:
        return None


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
            response = model.generate_content(prompt, safety_settings=_SAFETY_SETTINGS)
            text = _safe_chunk_text(response)

            return {
                "full_response": text or "",
                "model": model_name,
                "provider": "gemini",
            }

        except APIError:
            raise
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
            response = model.generate_content(prompt, stream=True, safety_settings=_SAFETY_SETTINGS)

            for chunk in response:
                text = _safe_chunk_text(chunk)
                if text:
                    yield text

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise APIError(
                ErrorCode.LLM_ERROR,
                {"provider": "gemini", "model": model_name, "details": str(e)},
            ) from e
