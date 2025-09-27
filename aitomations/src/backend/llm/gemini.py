# aitomations/src/backend/llm/gemini.py
import google.generativeai as genai
from .base import LLMProvider

class GeminiProvider(LLMProvider):
    def generate(self, prompt: str, options: dict) -> dict:
        api_key = options.get("gemini_api_key")
        model_name = options.get("gemini_model", "gemini-1.5-flash")
        if not api_key:
            raise ValueError("Gemini API key not configured.")
        genai.configure(api_key=api_key)
        print(f"[INFO] Calling Gemini with model {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        full_response_text = response.text
        print(f"[TRACE] Raw response from Gemini:\n---\n{full_response_text}\n---")

        return {
            "full_response": full_response_text,
        }