import os
import requests
import json
import yaml
from flask import Flask, request, jsonify, send_from_directory

# This is a critical security step for add-ons.
# The SUPERVISOR_TOKEN is provided by the Home Assistant Supervisor.
SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN')
if not SUPERVISOR_TOKEN:
    # Fallback for local development
    print("WARNING: SUPERVISOR_TOKEN not found. Using a dummy token for local dev.")
    SUPERVISOR_TOKEN = "dummy_token"

# Retrieve add-on configuration from environment variables
LLM_PROVIDER = os.environ.get('LLM_PROVIDER')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL')
# The HOST_IP is available via the S6 overlay environment variables if host_network is enabled
HOST_IP = os.environ.get('HOST_IP', 'localhost')

app = Flask(__name__, static_folder='static', static_url_path='/')

@app.route('/')
def serve_index():
    """Serves the main frontend application."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serves static assets like CSS and JS files."""
    return send_from_directory(app.static_folder, path)

def get_ha_data(endpoint):
    """
    Fetches data from a specific Home Assistant API endpoint using the
    Supervisor token for authentication.
    """
    url = f"http://supervisor/core/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from HA API at {url}: {e}")
        return None

def format_ha_config_for_llm():
    """
    Fetches a summary of Home Assistant entities, automations, and scenes
    and formats it into a string for the LLM prompt.
    """
    entity_data = get_ha_data("states")
    automation_data = get_ha_data("automations")
    scene_data = get_ha_data("scenes")

    ha_config = "Home Assistant Configuration:\n\n"
    
    if entity_data:
        ha_config += "Entities:\n"
        for entity in entity_data:
            state = entity.get('state', 'unknown')
            attributes = entity.get('attributes', {})
            friendly_name = attributes.get('friendly_name', entity['entity_id'])
            ha_config += f" - {friendly_name} ({entity['entity_id']}): state is '{state}'"
            if 'unit_of_measurement' in attributes:
                ha_config += f" {attributes['unit_of_measurement']}"
            ha_config += "\n"

    if automation_data:
        ha_config += "\nExisting Automations:\n"
        for auto in automation_data:
            ha_config += f" - {auto.get('alias', auto['id'])}\n"
    
    if scene_data:
        ha_config += "\nExisting Scenes:\n"
        for scene in scene_data:
            ha_config += f" - {scene.get('name', scene['id'])}\n"
            
    return ha_config

def call_ollama(prompt, ha_context):
    """Calls the Ollama LLM to generate an automation."""
    if not OLLAMA_API_URL:
        raise ValueError("OLLAMA_API_URL not configured.")
    
    full_prompt = (
        f"You are a helpful assistant for creating Home Assistant automations. "
        f"Based on the following Home Assistant configuration and user prompt, "
        f"generate a Home Assistant automation in YAML format. The YAML must "
        f"be a single YAML document. Do not include any YAML headers or footers, "
        f"just the automation content. Also, provide a brief, single-sentence summary of the automation. "
        f"The response MUST be a valid JSON object with a 'summary' key and a 'yaml' key. "
        f"Use single quotes for the summary value and triple quotes for the yaml value. "
        f"Example format: {{'summary': 'A brief summary of the automation.', 'yaml': '...automation yaml...'}}\n\n"
        f"Home Assistant Configuration:\n{ha_context}\n\n"
        f"User Prompt:\n{prompt}"
    )
    
    payload = {
        "model": "llama3",  # Assuming a capable model is available
        "prompt": full_prompt,
        "stream": False,
        "format": "json"
    }
    
    response = requests.post(OLLAMA_API_URL, json=payload)
    response.raise_for_status()
    result = response.json()
    
    # Ollama's response format can vary, so we extract the generated content
    return json.loads(result.get('response'))

def call_gemini(prompt, ha_context):
    """Calls the Gemini LLM to generate an automation."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    full_prompt = (
        f"You are a helpful assistant for creating Home Assistant automations. "
        f"Based on the following Home Assistant configuration and user prompt, "
        f"generate a Home Assistant automation in YAML format. The YAML must "
        f"be a single YAML document. Do not include any YAML headers or footers, "
        f"just the automation content. Also, provide a brief, single-sentence summary of the automation. "
        f"The response MUST be a valid JSON object with a 'summary' key and a 'yaml' key. "
        f"Example format: {{'summary': 'A brief summary of the automation.', 'yaml': '...automation yaml...'}}\n\n"
        f"Home Assistant Configuration:\n{ha_context}\n\n"
        f"User Prompt:\n{prompt}"
    )

    payload = {
        "contents": [{
            "parts": [{ "text": full_prompt }]
        }]
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()
    result = response.json()
    
    # Gemini response can be complex, extract the text part
    gemini_text = result['candidates'][0]['content']['parts'][0]['text']
    # Attempt to parse the JSON string from the LLM's text output
    return json.loads(gemini_text)

@app.route('/api/generate_automation', methods=['POST'])
def generate_automation():
    """
    Main endpoint to generate an automation.
    1. Fetches Home Assistant context.
    2. Calls the selected LLM with the context and user prompt.
    3. Returns the generated summary and YAML to the frontend.
    """
    data = request.get_json()
    user_prompt = data.get('prompt')
    if not user_prompt:
        return jsonify({"error": "Prompt is required."}), 400
    
    try:
        ha_context = format_ha_config_for_llm()
        
        if LLM_PROVIDER == 'ollama':
            llm_response = call_ollama(user_prompt, ha_context)
        elif LLM_PROVIDER == 'gemini':
            llm_response = call_gemini(user_prompt, ha_context)
        else:
            return jsonify({"error": "Invalid LLM provider specified."}), 400
            
        summary = llm_response.get('summary', 'No summary provided by LLM.')
        yaml_content = llm_response.get('yaml', 'No YAML provided by LLM.')
        
        # Validate that the LLM returned valid YAML
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return jsonify({"error": "LLM returned invalid YAML."}), 500
            
        return jsonify({
            "summary": summary,
            "yaml": yaml_content
        })
        
    except requests.exceptions.RequestException as e:
        print(f"LLM API request failed: {e}")
        return jsonify({"error": f"LLM API request failed. Please check your configuration and network connection: {e}"}), 500
    except (ValueError, KeyError, TypeError) as e:
        print(f"Error parsing LLM response or invalid configuration: {e}")
        return jsonify({"error": f"Error with LLM response or add-on configuration: {e}"}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@app.route('/api/install_automation', methods=['POST'])
def install_automation():
    """
    Endpoint to install the generated automation.
    In a real implementation, this would use the Home Assistant WebSocket API
    to add and reload the automation configuration.
    """
    data = request.get_json()
    automation_yaml = data.get('yaml')
    
    if not automation_yaml:
        return jsonify({"error": "Automation YAML is required."}), 400
    
    # --- IMPORTANT: REAL IMPLEMENTATION DETAILS ---
    # The simplest, most robust way to install an automation via an add-on is
    # to write the YAML content to a file in a configuration package (e.g., config/packages/llm_automations.yaml)
    # and then call the 'automation.reload' service via the Home Assistant WebSocket API.
    # The Supervisor API does not expose a REST endpoint to add automations directly.
    # This example only simulates success for demonstration purposes.

    print("Simulating automation installation...")
    print("Received YAML:")
    print(automation_yaml)
    
    # In a full implementation, you'd perform the following steps:
    # 1. Connect to HA's WebSocket API.
    # 2. Authenticate using the SUPERVISOR_TOKEN.
    # 3. Use the 'config/set_value' command to save the automation to a configuration file.
    # 4. Use the 'automation/reload' service call to make HA recognize the new automation.
    
    return jsonify({
        "status": "success",
        "message": "Automation installation request received. A full implementation would now communicate with the Home Assistant API to write and reload the configuration."
    })

if __name__ == '__main__':
    # For standalone testing with a local Flask server
    # Note: In production, Gunicorn will run the app.
    app.run(debug=True, host='0.0.0.0', port=8099)
