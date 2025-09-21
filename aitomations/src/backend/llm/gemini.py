import google.generativeai as genai
from .base import LLMProvider
from ..utils import extract_json_from_string

class GeminiProvider(LLMProvider):
    def generate(self, prompt: str, options: dict) -> dict:
        api_key = options.get('gemini_api_key')
        if not api_key:
            raise ValueError('Gemini API key not configured')

        model_name = options.get('gemini_model', 'gemini-1.5-pro')
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        print(f"[INFO] Calling Gemini with model {model_name}")
        response = model.generate_content(prompt)

        print(f"[TRACE] Raw response from Gemini:\n---\n{response.text}\n---")
        return extract_json_from_string(response.text)