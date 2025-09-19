import os
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import google.generativeai as genai

app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)

# Path to the options file in a Home Assistant add-on
OPTIONS_FILE = '/data/options.json'

def get_options():
    """Read options from the JSON file."""
    try:
        with open(OPTIONS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default structure if file doesn't exist or is empty/corrupt
        return {
            'ollama_api_url': 'http://ollama:11434/api/generate',
            'ollama_model': 'llama3',
            'gemini_api_key': '',
            'gemini_model': 'gemini-1.5-flash',
            'llm_provider': 'ollama'
        }

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/health')
def health_check():
    """Simple health check endpoint."""
    return jsonify({'status': 'healthy'})

@app.route('/api/config')
def get_config():
    """Get current configuration (excluding sensitive data)."""
    options = get_options()
    safe_config = {k: ('***' if 'key' in k.lower() and v else v) for k, v in options.items()}
    return jsonify(safe_config)

@app.route('/api/generate_automation', methods=['POST'])
def generate_automation():
    """Generate automation using selected LLM provider."""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data or not data['prompt']:
            return jsonify({'error': 'A non-empty prompt is required'}), 400
        
        options = get_options()
        llm_provider = options.get('llm_provider', 'ollama')
        prompt = data['prompt']
        
        print(f"[INFO] Generating automation with {llm_provider} for prompt: {prompt[:100]}...")
        
        if llm_provider == 'ollama':
            return generate_with_ollama(prompt, options)
        elif llm_provider == 'gemini':
            return generate_with_gemini(prompt, options)
        else:
            return jsonify({'error': f'Unknown LLM provider: {llm_provider}'}), 400
            
    except Exception as e:
        print(f"[ERROR] Error in generate_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/install_automation', methods=['POST'])
def install_automation():
    """Install automation into Home Assistant."""
    try:
        data = request.get_json()
        if not data or 'automation_yaml' not in data or not data['automation_yaml']:
            return jsonify({'error': 'Automation YAML is required'}), 400
        
        automation_yaml = data['automation_yaml']
        print(f"[INFO] Installing automation: {automation_yaml[:200]}...")
        
        # TODO: Implement actual Home Assistant API integration
        return jsonify({
            'success': True,
            'message': 'Automation would be installed (not implemented yet)',
        })
        
    except Exception as e:
        print(f"[ERROR] Error in install_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# LLM HELPER FUNCTIONS
# ============================================================================

def generate_with_ollama(prompt, options):
    """Generate automation using Ollama."""
    # ... (Ollama implementation remains the same)
    try:
        ollama_url = options.get('ollama_api_url', 'http://ollama:11434/api/generate')
        model = options.get('ollama_model', 'llama3')
        
        automation_prompt = f"""Create a detailed Home Assistant automation for the following request:
{prompt}

Please provide your response as JSON with these exact fields:
- "summary": A clear description of what the automation does
- "yaml": The complete Home Assistant automation YAML configuration"""
        
        payload = {'model': model, 'prompt': automation_prompt, 'stream': False}
        
        print(f"[INFO] Calling Ollama at {ollama_url}")
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        automation_text = result.get('response', '')
        
        try:
            return jsonify(json.loads(automation_text))
        except json.JSONDecodeError:
            print(f"[WARN] Ollama response was not valid JSON. Returning as text. Response: {automation_text[:200]}")
            return jsonify({'summary': f'Generated automation for: {prompt}', 'yaml': automation_text})
        
    except Exception as e:
        print(f"[ERROR] Ollama error: {str(e)}")
        return jsonify({'error': f'Ollama error: {str(e)}'}), 500

def generate_with_gemini(prompt, options):
    """Generate automation using Google Gemini."""
    try:
        api_key = options.get('gemini_api_key')
        if not api_key:
            return jsonify({'error': 'Gemini API key not configured'}), 400
        
        model_name = options.get('gemini_model', 'gemini-2.5-pro')
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        automation_prompt = f"""Create a detailed Home Assistant automation for the following request:
{prompt}

Please provide your response as JSON with these exact fields:
- "summary": A clear description of what the automation does
- "yaml": The complete Home Assistant automation YAML configuration

Example format:
{{
  "summary": "Turns on lights when motion detected after sunset",
  "yaml": "alias: Motion Light\\ntrigger:\\n  - platform: state\\n    entity_id: binary_sensor.motion\\n    to: 'on'\\ncondition:\\n  - condition: sun\\n    after: sunset\\naction:\\n  - service: light.turn_on\\n    target:\\n      entity_id: light.living_room"
}}

Make sure the YAML is valid Home Assistant automation syntax."""
        
        print(f"[INFO] Calling Gemini with model {model_name}")
        response = model.generate_content(automation_prompt)
        
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        
        try:
            return jsonify(json.loads(response_text))
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse Gemini JSON response: {e}")
            print(f"[ERROR] Raw response: {response.text}")
            return jsonify({'summary': f'Generated automation for: {prompt}', 'yaml': response.text})
        
    except Exception as e:
        print(f"[ERROR] Gemini error: {str(e)}")
        return jsonify({'error': f'Gemini error: {str(e)}'}), 500

# ============================================================================
# FRONTEND SERVING - Catch-all route for SPA
# ============================================================================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    """Serve the Vue.js application."""
    static_folder = app.static_folder
    
    # If the path points to an existing file in the static folder, serve it
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    
    # Otherwise, serve the index.html for SPA routing
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder, 'index.html')
    else:
        return jsonify({'error': 'Frontend not found. Please build the frontend.'}), 404

if __name__ == '__main__':
    print("🚀 Starting AItomations Flask backend...")
    app.run(host='0.0.0.0', port=8099, debug=False)
