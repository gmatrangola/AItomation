# AItomations Creator Documentation

## Installation

Add this repository to your Home Assistant:

```
https://github.com/gmatrangola/aitomation-install
```

Then install the **AItomations Creator** add-on.

## Configuration Options

### `llm_provider` (required)

Choose your AI provider:
- `gemini` - Google's Gemini AI (cloud-based)
- `ollama` - Local Ollama installation

### `gemini_api_key` (required for Gemini)

Your Google AI API key. Get one at [Google AI Studio](https://makersuite.google.com/app/apikey).

**Free tier**: 15 requests per minute, 1 million tokens per minute

### `ollama_api_url` (required for Ollama)

The full URL to your Ollama API endpoint.

Examples:
- `http://192.168.1.100:11434/api/generate`
- `http://homeassistant.local:11434/api/generate`

### `ollama_model` (optional)

The Ollama model to use. Default: `llama3.2:latest`

Recommended models:
- `llama3.2:latest` (3B - fast, good quality)
- `llama3.1:latest` (8B - slower, better quality)
- `codellama:latest` (specialized for code)

### `request_timeout` (optional)

Timeout for API requests in seconds. Default: 120

Range: 30-600 seconds

## Usage Guide

### Creating Your First Automation

1. Open the Web UI
2. Type a description like: "Turn on kitchen lights when motion is detected"
3. Wait for the AI to generate the automation
4. Review the YAML code and explanation
5. Click **Install Automation** to add it to Home Assistant

### Tips for Better Results

**Be specific about:**
- Entity names (use actual device names from your setup)
- Times and conditions
- Actions you want to happen

**Good prompts:**
```
Turn on the living room lights at sunset if someone is home
Send me a notification when the front door is open for more than 5 minutes
Set the bedroom temperature to 68°F at 10 PM on weekdays
```

**The AI knows your entities**, so it will suggest the correct ones!

### Conversational Refinement

You can refine automations through conversation:
1. Generate an automation
2. Ask to modify it: "Make the delay 10 minutes instead"
3. The AI will update the automation
4. Install when satisfied

## Troubleshooting

### "API key not configured"

**Solution**: Add your Gemini API key or Ollama URL in the Configuration tab.

### "Connection refused" (Ollama)

**Possible causes:**
- Ollama not running
- Wrong URL or port
- Firewall blocking connection

**Solution**: 
- Verify Ollama is running: `curl http://your-ollama-url:11434/api/tags`
- Check firewall settings
- Ensure the URL includes the full path: `/api/generate`

### "Model not found" (Ollama)

**Solution**: Pull the model first:
```bash
ollama pull llama3.2:latest
```

### Automation not working as expected

**Tips:**
- Be more specific in your description
- Mention exact entity names
- Ask the AI to explain what the automation does
- Use the conversation to refine it

### Add-on won't start

**Check logs:**
Settings → Add-ons → AItomations Creator → Logs

**Common issues:**
- Invalid API key format
- Configuration syntax errors
- Network connectivity issues

## Advanced Configuration

### Using with Home Assistant Ollama Add-on

If you're running the Ollama add-on in Home Assistant:

```yaml
llm_provider: ollama
ollama_api_url: http://homeassistant.local:11434/api/generate
ollama_model: llama3.2:latest
```

### Rate Limiting (Gemini)

Free tier limits:
- 15 requests per minute
- 1 million tokens per minute

The add-on automatically handles rate limiting and retries.

### Security Best Practices

1. **API Keys**: Treat them like passwords - never share publicly
2. **Network**: Consider using Ollama locally for privacy
3. **Validation**: Always review generated automations before installing

## FAQ

**Q: Does this work offline?**  
A: Yes, if you use Ollama locally. Gemini requires internet.

**Q: What data is sent to Google?**  
A: Your prompt and your Home Assistant entity list. No automation state or history.

**Q: Can I use other AI models?**  
A: Currently supports Gemini and Ollama. More providers coming soon!

**Q: Will this break my existing automations?**  
A: No. Generated automations are standalone and don't modify existing ones.

**Q: Can I edit generated automations?**  
A: Yes! After installing, edit them in Settings → Automations & Scenes.

## Support

- [GitHub Issues](https://github.com/gmatrangola/AItomation/issues)
- [Discussions](https://github.com/gmatrangola/AItomation/discussions)
- [Home Assistant Community](https://community.home-assistant.io/)