import requests
from .base import LLMProvider
from ..utils import extract_json_from_string

class OllamaProvider(LLMProvider):
    def generate(self, prompt: str, options: dict) -> dict:
        ollama_url = options.get('ollama_api_url', 'http://ollama:11434/api/generate')
        model = options.get('ollama_model', 'llama3')
        payload = {'model': model, 'prompt': prompt, 'stream': False}

        print(f"[INFO] Calling Ollama at {ollama_url}")
        response = requests.post(ollama_url, json=payload, timeout=60)
        response.raise_for_status()

        automation_text = response.json().get('response', '')
        print(f"[TRACE] Raw response from Ollama:\n---\n{automation_text}\n---")
        return extract_json_from_string(automation_text)