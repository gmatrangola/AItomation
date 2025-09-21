import os
import json
import re
import time
import yaml
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import google.generativeai as genai

app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)

# --- Home Assistant API Configuration ---
HA_API_URL = "http://supervisor/core/api"
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

# Path to the options file in a Home Assistant add-on
OPTIONS_FILE = '/data/options.json'

# --- Metadata Key ---
AITOMATIONS_METADATA_KEY = "aitomations_metadata"

def get_options():
    """Read options from the JSON file."""
    try:
        with open(OPTIONS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
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

@app.route('/api/automations')
def get_automations():
    """Fetches a list of all automations and their AItomations metadata."""
    print("[INFO] /api/automations endpoint called.")
    if not SUPERVISOR_TOKEN:
        print("[ERROR] Supervisor token not found.")
        return jsonify({"error": "Supervisor token not found"}), 500
    try:
        # 1. Get all automation states first, as this is the source of truth for what exists.
        print("[INFO] Fetching all states from HA to find automations...")
        states_response = requests.get(f"{HA_API_URL}/states", headers=HA_HEADERS, timeout=15)
        states_response.raise_for_status()
        
        automation_entities = [s for s in states_response.json() if s['entity_id'].startswith('automation.')]
        print(f"[INFO] Found {len(automation_entities)} automation entities.")

        if not automation_entities:
            print("[WARN] No automation entities found in Home Assistant states.")
            return jsonify([])

        processed_automations = []
        # 2. Loop through each found automation entity and get its specific config.
        for entity in automation_entities:
            entity_id = entity['entity_id']
            automation_id = entity_id.split('.', 1)[1]

            print(f"[DEBUG] Processing entity: {entity_id}")
            config_response = requests.get(f"{HA_API_URL}/config/automation/config/{automation_id}", headers=HA_HEADERS, timeout=10)

            # Default values from the entity state itself
            item = {
                "id": automation_id,
                "entity_id": entity_id,
                "alias": entity['attributes'].get('friendly_name', automation_id.replace('_', ' ').title()),
                "state": entity['state'],
                "prompt": None,
                "source": None,
                "is_editable": False # Assume not editable by default
            }

            if config_response.status_code == 200:
                # This automation has an ID and is editable via the API
                config = config_response.json()
                metadata = config.get(AITOMATIONS_METADATA_KEY, {})
                item['id'] = config.get('id', automation_id) # Prefer the ID from config
                item['alias'] = config.get('alias', item['alias'])
                item['prompt'] = metadata.get('prompt')
                item['source'] = metadata.get('source')
                item['is_editable'] = True
                print(f"[DEBUG] Successfully fetched editable config for {entity_id}")
            else:
                # This automation does not have an 'id' and is not editable via API
                print(f"[WARN] Could not fetch config for {entity_id} (Status: {config_response.status_code}). Marking as non-editable.")

            processed_automations.append(item)

        print(f"[INFO] Returning {len(processed_automations)} processed automations to frontend.")
        return jsonify(processed_automations)

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not connect to Home Assistant API: {e}")
        return jsonify({"error": f"Could not connect to Home Assistant API: {e}"}), 500
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred in get_automations: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


def _extract_json_from_string(text):
    """Finds and extracts the first valid JSON object from a string."""
    try:
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_str = text[start_index : end_index + 1]
            return json.loads(json_str)
        else:
            raise ValueError("No valid JSON object found in the string.")
    except (json.JSONDecodeError, ValueError) as e:
        # This log is crucial for debugging LLM responses
        print(f"[ERROR] Failed to extract JSON. Error: {e}.")
        print(f"[TRACE] Raw text for JSON extraction failure:\n---\n{text}\n---")
        raise

def _get_ha_context():
    """Fetches entities, services, and automations from Home Assistant."""
    if not SUPERVISOR_TOKEN:
        raise ConnectionError("Supervisor token not found. Cannot connect to Home Assistant.")
    try:
        states_response = requests.get(f"{HA_API_URL}/states", headers=HA_HEADERS, timeout=10)
        states_response.raise_for_status()
        all_states = states_response.json()

        entities = [{"id": e["entity_id"], "name": e["attributes"].get("friendly_name", e["entity_id"])} for e in all_states]
        automations = [{"id": s["entity_id"], "name": s["attributes"].get("friendly_name", s["entity_id"])} for s in all_states if s["entity_id"].startswith("automation.")]
        
        services_response = requests.get(f"{HA_API_URL}/services", headers=HA_HEADERS, timeout=10)
        services_response.raise_for_status()
        services = [f"{domain['domain']}.{service}" for domain in services_response.json() for service in domain["services"]]

        context_data = {"entities": entities, "services": services, "automations": automations}
        summary = f"Context: {len(entities)} entities, {len(services)} services, and {len(automations)} automations from Home Assistant."
        return context_data, summary
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not fetch Home Assistant context: {e}")
        raise ConnectionError(f"Could not connect to Home Assistant API: {e}")

@app.route('/api/generate_automation', methods=['POST'])
def generate_automation():
    """Generate automation using selected LLM provider."""
    print("[INFO] /api/generate_automation endpoint called.")
    try:
        data = request.get_json()
        if not data or 'prompt' not in data or not data['prompt']:
            return jsonify({'error': 'A non-empty prompt is required'}), 400
        
        print("[INFO] Fetching HA context for generation...")
        ha_context, context_summary = _get_ha_context()
        options = get_options()
        llm_provider = options.get('llm_provider', 'ollama')
        prompt = data['prompt']
        
        # This is the prompt for creating a new automation
        creation_prompt = f"""You are an expert Home Assistant automation assistant. Your task is to help users without creating duplicate automations.
**Step 1: Check for Similar Automations**
Review the user's request and compare it against the list of existing automations provided in the Home Assistant Context.
**Home Assistant Context:**
{json.dumps(ha_context, indent=2)}
**User Request:**
{prompt}
If you find one or more automations that seem to perform a similar function, respond ONLY with a JSON object with a single key "similar_automations".
Example: {{ "similar_automations": [ {{ "entity_id": "automation.lights_on_at_sunset", "reason": "This already turns on lights." }} ] }}
**Step 2: Generate a New Automation**
If, and ONLY IF, you find NO similar automations, then generate a new one. Your response must be a single JSON object with "summary" and "yaml" keys.
Example: {{ "summary": "Turns on the living room light.", "yaml": "alias: New Motion Light\\n..." }}
Analyze the user's request and provide the appropriate JSON response.
"""
        
        print(f"[INFO] Generating new automation with {llm_provider} for prompt: '{prompt[:100]}...'")
        if llm_provider == 'ollama':
            llm_response = generate_with_ollama(creation_prompt, options)
        else:
            llm_response = generate_with_gemini(creation_prompt, options)
        
        response_data = llm_response.get_json()
        response_data['context_summary'] = context_summary
        response_data['prompt'] = prompt
        
        print(f"[DEBUG] Successfully parsed LLM response. Returning to frontend.")
        return jsonify(response_data)
    except ConnectionError as e:
        print(f"[ERROR] Connection error in generate_automation: {e}")
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        print(f"[ERROR] Error in generate_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/edit_automation', methods=['POST'])
def edit_automation():
    """Receives an existing automation's YAML and a new prompt to modify it."""
    try:
        data = request.get_json()
        if not all(k in data for k in ['automation_id', 'prompt']):
            return jsonify({'error': 'automation_id and prompt are required'}), 400

        config_response = requests.get(f"{HA_API_URL}/config/automation/config/{data['automation_id']}", headers=HA_HEADERS)
        config_response.raise_for_status()
        existing_config = config_response.json()
        
        if AITOMATIONS_METADATA_KEY in existing_config:
            del existing_config[AITOMATIONS_METADATA_KEY]
        
        existing_yaml = yaml.dump(existing_config)
        ha_context, context_summary = _get_ha_context()
        options = get_options()
        llm_provider = options.get('llm_provider', 'ollama')
        
        edit_prompt = f"""You are an expert Home Assistant automation editor.
Given an existing automation's YAML, modify it based on the user's request.
The 'id' field MUST NOT be changed.
**Existing Automation YAML:**
```yaml
{existing_yaml}
```
**User's Modification Request:**
{data['prompt']}
Respond ONLY with a JSON object containing the "summary" of the changes and the complete, updated "yaml".
"""
        
        if llm_provider == 'ollama':
            llm_response = generate_with_ollama(edit_prompt, options)
        else:
            llm_response = generate_with_gemini(edit_prompt, options)

        response_data = llm_response.get_json()
        response_data['context_summary'] = context_summary
        response_data['prompt'] = data['prompt']
        return jsonify(response_data)
    except Exception as e:
        print(f"[ERROR] Error in edit_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/install_automation', methods=['POST'])
def install_automation():
    """Install automation into Home Assistant."""
    if not SUPERVISOR_TOKEN:
        return jsonify({"error": "Supervisor token not found"}), 500
    try:
        data = request.get_json()
        if not data or 'automation_yaml' not in data:
            return jsonify({'error': 'Automation YAML is required'}), 400
        
        automation_yaml = data['automation_yaml']
        prompt = data.get('prompt')
        
        try:
            config = yaml.safe_load(automation_yaml)
            if isinstance(config, list):
                config = config[0]
        except yaml.YAMLError as e:
            return jsonify({'error': f'Invalid YAML format: {e}'}), 400

        if prompt:
            options = get_options()
            config[AITOMATIONS_METADATA_KEY] = {
                'source': 'aitomations_addon',
                'prompt': prompt,
                'llm_provider': options.get('llm_provider'),
                'model': options.get('gemini_model') if options.get('llm_provider') == 'gemini' else options.get('ollama_model'),
                'timestamp': int(time.time())
            }

        # Generate a unique ID for the automation if it doesn't have one
        if 'id' not in config or not config['id']:
            alias = config.get('alias', 'New AItomation')
            # Create a slug-like ID and add a timestamp
            slug = re.sub(r'[^\w-]', '', re.sub(r'\s+', '_', alias).lower())
            config['id'] = f"{slug}_{int(time.time())}"

        print(f"[INFO] Installing automation with ID: {config['id']}")
        install_url = f"http://supervisor/core/api/config/automation/config/{config['id']}"
        
        response = requests.post(install_url, headers=HA_HEADERS, json=config, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        if result.get('result') == 'ok':
            print(f"[SUCCESS] Automation '{config.get('alias')}' installed successfully.")
            return jsonify({'success': True, 'message': f"Automation '{config.get('alias')}' installed."})
        else:
            raise Exception(f"Failed to install automation: {response.text}")
    except requests.exceptions.RequestException as e:
        error_message = f"API call to Home Assistant failed: {e}"
        if e.response is not None: error_message += f" | Response: {e.response.text}"
        print(f"[ERROR] {error_message}")
        return jsonify({'error': error_message}), 500
    except Exception as e:
        print(f"[ERROR] Error in install_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# LLM HELPER FUNCTIONS
# ============================================================================

def generate_with_ollama(prompt, options):
    """Generic Ollama generation function."""
    try:
        ollama_url = options.get('ollama_api_url', 'http://ollama:11434/api/generate')
        model = options.get('ollama_model', 'llama3')
        payload = {'model': model, 'prompt': prompt, 'stream': False}
        
        print(f"[INFO] Calling Ollama at {ollama_url}")
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        
        automation_text = response.json().get('response', '')
        print(f"[TRACE] Raw response from Ollama:\n---\n{automation_text}\n---")
        parsed_json = _extract_json_from_string(automation_text)
        return jsonify(parsed_json)
    except Exception as e:
        print(f"[ERROR] Ollama error: {str(e)}")
        return jsonify({'error': f'Ollama error: {str(e)}'}), 500

def generate_with_gemini(prompt, options):
    """Generic Gemini generation function."""
    try:
        api_key = options.get('gemini_api_key')
        if not api_key:
            return jsonify({'error': 'Gemini API key not configured'}), 400
        
        model_name = options.get('gemini_model', 'gemini-2.5-pro')
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        print(f"[INFO] Calling Gemini with model {model_name}")
        response = model.generate_content(prompt)
        
        print(f"[TRACE] Raw response from Gemini:\n---\n{response.text}\n---")
        parsed_json = _extract_json_from_string(response.text)
        return jsonify(parsed_json)
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
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    index_path = os.path.join(static_folder, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder, 'index.html')
    else:
        return jsonify({'error': 'Frontend not found. Please build the frontend.'}), 404

if __name__ == '__main__':
    print("🚀 Starting AItomations Flask backend...")
    app.run(host='0.0.0.0', port=8099, debug=False)
