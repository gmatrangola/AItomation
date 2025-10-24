import json
import logging
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import requests

from api.errors import APIError, ErrorCode
from api.network import resolve_hostname, test_connection

from .base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """Generate text using Ollama (non-streaming)."""
        ollama_api_url = options.get("ollama_api_url", "http://localhost:11434/api/generate")
        model = options.get("ollama_model", "llama3")
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2048)
        request_timeout = options.get("request_timeout", 120)

        if "/api/generate" in ollama_api_url:
            base_url = ollama_api_url.replace("/api/generate", "")
        else:
            base_url = ollama_api_url
            ollama_api_url = f"{base_url}/api/generate"

        # Resolve hostname
        try:
            resolved_base = resolve_hostname(base_url.rstrip("/"))
            url = f"{resolved_base}/api/generate"
        except ValueError as e:
            raise APIError(
                ErrorCode.HOSTNAME_RESOLUTION_FAILED,
                {"hostname": base_url, "provider": "ollama"},
            ) from e

        # Test connection - wrap in try-except to catch port parsing errors
        try:
            parsed = urlparse(resolved_base)
            hostname = parsed.hostname or "localhost"
            # This is where ValueError can be raised for invalid port
            port = parsed.port or 11434
        except ValueError as e:
            # Invalid port number in URL
            raise APIError(
                ErrorCode.INVALID_CONFIG,
                {
                    "provider": "ollama",
                    "url": base_url,
                    "details": str(e),
                },
            ) from e

        if not test_connection(hostname, port, timeout=3.0):
            raise APIError(
                ErrorCode.CONNECTION_REFUSED,
                {
                    "hostname": hostname,
                    "port": port,
                    "provider": "ollama",
                    "url": resolved_base,
                },
            )

        logger.info(f"Calling Ollama at {url} with model {model}")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=request_timeout)
            response.raise_for_status()
            result = response.json()
            full_response = result.get("response", "")

            return {"full_response": full_response, "model": model, "provider": "ollama"}

        except requests.exceptions.ConnectionError as e:
            raise APIError(
                ErrorCode.CONNECTION_LOST,
                {"provider": "ollama", "url": url},
            ) from e

        except requests.exceptions.Timeout as e:
            raise APIError(
                ErrorCode.REQUEST_TIMEOUT,
                {
                    "provider": "ollama",
                    "model": model,
                    "timeout": request_timeout,
                    "url": url,
                },
            ) from e

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            error_body = e.response.text if e.response else ""

            if status_code == 404:
                raise APIError(
                    ErrorCode.MODEL_NOT_FOUND,
                    {
                        "provider": "ollama",
                        "model": model,
                        "url": resolved_base,
                    },
                ) from e
            else:
                raise APIError(
                    ErrorCode.HTTP_ERROR,
                    {
                        "provider": "ollama",
                        "status_code": status_code,
                        "url": url,
                        "details": error_body[:500],
                    },
                ) from e

        except requests.exceptions.RequestException as e:
            raise APIError(
                ErrorCode.NETWORK_ERROR,
                {"provider": "ollama", "url": url, "details": str(e)},
            ) from e

    def generate_stream(self, prompt: str, options: dict[str, Any]) -> Iterator[str]:
        """Generate text using Ollama with streaming."""
        ollama_api_url = options.get("ollama_api_url", "http://localhost:11434/api/generate")
        model = options.get("ollama_model", "llama3")
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2048)
        request_timeout = options.get("request_timeout", 120)

        if "/api/generate" in ollama_api_url:
            base_url = ollama_api_url.replace("/api/generate", "")
        else:
            base_url = ollama_api_url
            ollama_api_url = f"{base_url}/api/generate"

        try:
            resolved_base = resolve_hostname(base_url.rstrip("/"))
            url = f"{resolved_base}/api/generate"
        except ValueError as e:
            raise APIError(
                ErrorCode.HOSTNAME_RESOLUTION_FAILED,
                {"hostname": base_url, "provider": "ollama"},
            ) from e

        # Wrap port parsing in try-except to catch ValueError
        try:
            parsed = urlparse(resolved_base)
            hostname = parsed.hostname or "localhost"
            # This line can raise ValueError for invalid port like '11434z'
            port = parsed.port or 11434
        except ValueError as e:
            # Invalid port number in URL
            raise APIError(
                ErrorCode.INVALID_CONFIG,
                {
                    "provider": "ollama",
                    "url": base_url,
                    "details": str(e),
                },
            ) from e

        if not test_connection(hostname, port, timeout=3.0):
            raise APIError(
                ErrorCode.CONNECTION_REFUSED,
                {
                    "hostname": hostname,
                    "port": port,
                    "provider": "ollama",
                    "url": resolved_base,
                },
            )

        logger.info(f"Streaming from Ollama at {url} with model {model}")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=request_timeout, stream=True)
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk

                        if data.get("done", False):
                            logger.info("Ollama streaming complete")
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse line: {line}")
                        continue

        except requests.exceptions.ConnectionError as e:
            raise APIError(
                ErrorCode.CONNECTION_LOST,
                {"provider": "ollama", "url": url},
            ) from e

        except requests.exceptions.Timeout as e:
            raise APIError(
                ErrorCode.REQUEST_TIMEOUT,
                {"provider": "ollama", "model": model, "timeout": request_timeout},
            ) from e

        except requests.exceptions.RequestException as e:
            raise APIError(
                ErrorCode.NETWORK_ERROR,
                {"provider": "ollama", "details": str(e)},
            ) from e
