import requests
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    def generate(self, prompt: str, options: dict) -> dict:
        ollama_url = options.get("ollama_api_url")
        model_name = options.get("ollama_model")

        if not all([ollama_url, model_name]):
            raise ValueError("Ollama URL or model not configured.")

        print(f"[INFO] Calling Ollama at {ollama_url} with model {model_name}")

        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()
            full_response_text = response.json().get("response", "")
            print(f"[TRACE] Raw response from Ollama:\n---\n{full_response_text}\n---")

            return {
                "full_response": full_response_text,
            }
        except requests.RequestException as e:
            raise ConnectionError(f"Could not connect to Ollama: {e}")