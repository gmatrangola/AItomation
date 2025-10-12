import requests
import json
import logging
from urllib.parse import urlparse
from ..api.network import resolve_hostname, test_connection

logger = logging.getLogger(__name__)


class OllamaProvider:
    def generate(self, prompt: str, options: dict) -> dict:
        """Generate text using Ollama."""
        # Get the full API URL from options (includes /api/generate)
        ollama_api_url = options.get('ollama_api_url', 'http://localhost:11434/api/generate')
        model = options.get('ollama_model', 'llama3')
        temperature = options.get('temperature', 0.7)
        max_tokens = options.get('max_tokens', 2048)
        request_timeout = options.get('request_timeout', 120)  # Get timeout from config
        
        logger.info(f"Request timeout set to {request_timeout} seconds")
        
        # Extract base URL (without /api/generate) for resolution
        if '/api/generate' in ollama_api_url:
            base_url = ollama_api_url.replace('/api/generate', '')
        else:
            base_url = ollama_api_url
            ollama_api_url = f"{base_url}/api/generate"
        
        logger.info(f"Original base URL: {base_url}")
        
        # Resolve .local hostnames using mDNS
        try:
            resolved_base = resolve_hostname(base_url.rstrip('/'))
            url = f"{resolved_base}/api/generate"
            logger.info(f"Resolved URL: {url}")
        except ValueError as e:
            logger.error(f"Hostname resolution failed: {e}")
            raise ConnectionError(str(e))
        except Exception as e:
            error_msg = (
                f"❌ Unexpected error resolving hostname\n\n"
                f"**Configuration:** `{base_url}`\n\n"
                f"**Technical details:** {str(e)}"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        
        # Parse URL to test connection
        parsed = urlparse(resolved_base)
        hostname = parsed.hostname or 'localhost'
        port = parsed.port or 11434
        
        # Test connection before attempting request
        logger.info(f"Testing connection to Ollama at {hostname}:{port}")
        if not test_connection(hostname, port, timeout=3.0):
            error_msg = (
                f"❌ Cannot connect to Ollama server\n\n"
                f"**Server:** `{hostname}:{port}`\n\n"
                f"**Troubleshooting checklist:**\n"
                f"1. ✓ Verify Ollama is running on the host machine\n"
                f"   • Run: `ollama serve`\n"
                f"   • Or check if the Ollama service is active\n\n"
                f"2. ✓ Check if port {port} is accessible from Home Assistant\n"
                f"   • Firewall may be blocking the connection\n"
                f"   • Try accessing `{resolved_base}` from your browser\n\n"
                f"3. ✓ If Ollama is in Docker, ensure ports are exposed\n"
                f"   • Docker run command should include: `-p {port}:{port}`\n\n"
                f"4. ✓ Verify network connectivity\n"
                f"   • Can Home Assistant reach this host?\n"
                f"   • Are they on the same network/VLAN?\n\n"
                f"5. ✓ Check if `host_network: true` is set in config.json\n"
                f"   • This allows the addon to access the host network\n\n"
                f"**Configuration:** `{base_url}` → `{resolved_base}`"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        
        logger.info(f"Calling Ollama at {url} with model {model}")
        
        payload = {
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=request_timeout)
            response.raise_for_status()
            
            result = response.json()
            full_response = result.get('response', '')
            
            logger.info(f"Ollama response received, length: {len(full_response)}")
            
            return {
                'full_response': full_response,
                'model': model,
                'provider': 'ollama'
            }
            
        except requests.exceptions.ConnectionError as e:
            error_msg = (
                f"❌ Connection lost to Ollama server\n\n"
                f"**Server:** `{url}`\n\n"
                f"**What happened:**\n"
                f"The connection was established but then lost during the request.\n\n"
                f"**Try these steps:**\n"
                f"1. Check if Ollama is still running on the host\n"
                f"2. Look for Ollama errors in the host machine's logs\n"
                f"3. Verify network stability between Home Assistant and Ollama host\n"
                f"4. Try restarting the Ollama service\n\n"
                f"**Technical details:** {str(e)}"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg)
            
        except requests.exceptions.Timeout as e:
            error_msg = (
                f"⏱️ Request timed out after {request_timeout} seconds\n\n"
                f"**Model:** `{model}`\n"
                f"**Server:** `{url}`\n\n"
                f"**Possible causes:**\n"
                f"• The model '{model}' is not installed on the Ollama server\n"
                f"• The model is too large and taking too long to respond\n"
                f"• The Ollama server is under heavy load\n"
                f"• Network connection is too slow\n"
                f"• Timeout setting ({request_timeout}s) may be too short\n\n"
                f"**Solutions:**\n"
                f"1. Check if the model is installed:\n"
                f"   ```\n"
                f"   ollama list\n"
                f"   ```\n\n"
                f"2. Install the model if missing:\n"
                f"   ```\n"
                f"   ollama pull {model}\n"
                f"   ```\n\n"
                f"3. Try a smaller/faster model like:\n"
                f"   • `llama3.2:1b` (smallest)\n"
                f"   • `qwen2.5:3b`\n"
                f"   • `phi3:mini`\n\n"
                f"4. **Increase the timeout** in add-on Configuration tab\n"
                f"   • Current: {request_timeout}s\n"
                f"   • Try: 180s or 300s for larger models\n\n"
                f"5. Check Ollama server logs for errors\n\n"
                f"**Technical details:** {str(e)}"
            )
            logger.error(error_msg)
            raise TimeoutError(error_msg)
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'
            error_body = e.response.text if e.response else 'No response body'
            
            if status_code == 404:
                error_msg = (
                    f"❌ Model '{model}' not found on Ollama server\n\n"
                    f"**Server:** `{resolved_base}`\n\n"
                    f"**To fix this:**\n\n"
                    f"1. Install the model on your Ollama server:\n"
                    f"   ```\n"
                    f"   ollama pull {model}\n"
                    f"   ```\n\n"
                    f"2. Or choose a model that's already installed:\n"
                    f"   ```\n"
                    f"   ollama list\n"
                    f"   ```\n\n"
                    f"3. Update your add-on configuration with an available model\n\n"
                    f"**Popular models to try:**\n"
                    f"• `llama3.2` (default)\n"
                    f"• `qwen2.5:3b` (faster)\n"
                    f"• `phi3`\n"
                    f"• `mistral`\n\n"
                    f"**Server response:** {error_body[:200]}"
                )
            else:
                error_msg = (
                    f"❌ Ollama server returned an error\n\n"
                    f"**HTTP Status:** {status_code}\n"
                    f"**Server:** `{url}`\n\n"
                    f"**Server response:**\n"
                    f"```\n"
                    f"{error_body[:500]}\n"
                    f"```\n\n"
                    f"**What to do:**\n"
                    f"1. Check the Ollama server logs for more details\n"
                    f"2. If using Docker: `docker logs <ollama-container>`\n"
                    f"3. Verify your Ollama server is functioning:\n"
                    f"   • Try: `ollama run {model} 'Hello'`\n"
                    f"4. Restart the Ollama service if needed"
                )
            
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = (
                f"❌ Unexpected network error\n\n"
                f"**Server:** `{url}`\n\n"
                f"**What happened:**\n"
                f"An unexpected error occurred while communicating with Ollama.\n\n"
                f"**Troubleshooting:**\n"
                f"1. Check Ollama server logs for errors\n"
                f"2. Check Home Assistant add-on logs\n"
                f"3. Verify network connectivity is stable\n"
                f"4. Try restarting both Ollama and this add-on\n\n"
                f"**Configuration:** `{base_url}` → `{resolved_base}`\n\n"
                f"**Technical details:** {str(e)}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)