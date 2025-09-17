import os
import json
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
import requests
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Path to the options file in a Home Assistant add-on
OPTIONS_FILE = '/data/options.json'

# Path to the built Vue.js frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'dist')

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
            'gemini_model': 'gemini-pro',
            'llm_provider': 'ollama'
        }

# ============================================================================
# FRONTEND ROUTES - Serve Vue.js application
# ============================================================================

@app.route('/')
def index():
    """Serve the main Vue.js application"""
    try:
        index_path = os.path.join(STATIC_DIR, 'index.html')
        if os.path.exists(index_path):
            print(f"[INFO] Serving index.html from {index_path}")
            return send_from_directory(STATIC_DIR, 'index.html')
        else:
            return jsonify({
                'error': 'Frontend not found',
                'static_dir': STATIC_DIR,
                'index_exists': os.path.exists(index_path),
                'available_files': os.listdir(os.path.dirname(__file__)) if os.path.exists(os.path.dirname(__file__)) else []
            }), 404
    except Exception as e:
        print(f"[ERROR] Error serving index: {str(e)}")
        return f"Error serving index: {str(e)}", 500

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve Vue.js assets (CSS, JS, etc.)"""
    try:
        assets_dir = os.path.join(STATIC_DIR, 'assets')
        file_path = os.path.join(assets_dir, filename)
        
        print(f"[INFO] Requested asset: {filename}")
        print(f"[INFO] Looking in: {assets_dir}")
        print(f"[INFO] Full path: {file_path}")
        print(f"[INFO] File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_from_directory(assets_dir, filename)
        else:
            print(f"[ERROR] Asset not found: {filename}")
            # List available assets for debugging
            if os.path.exists(assets_dir):
                available = os.listdir(assets_dir)
                print(f"[INFO] Available assets: {available}")
            return f"Asset not found: {filename}", 404
    except Exception as e:
        print(f"[ERROR] Error serving asset {filename}: {str(e)}")
        return f"Error serving asset: {str(e)}", 500

@app.route('/vite.svg')
def serve_vite_svg():
    """Serve the Vite favicon"""
    vite_svg_path = os.path.join(STATIC_DIR, 'vite.svg')
    if os.path.exists(vite_svg_path):
        return send_from_directory(STATIC_DIR, 'vite.svg')
    return "Favicon not found", 404

@app.route('/<path:path>')
def serve_static_or_spa(path):
    """Serve static files or handle SPA routing"""
    try:
        # First try to serve as a static file
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.exists(file_path):
            return send_from_directory(STATIC_DIR, path)
        
        # If it's not a file and doesn't have an extension, treat as SPA route
        if '.' not in path and os.path.exists(os.path.join(STATIC_DIR, 'index.html')):
            return send_from_directory(STATIC_DIR, 'index.html')
        
        # File not found
        print(f"[ERROR] File not found: {path}")
        return f"File not found: {path}", 404
    except Exception as e:
        print(f"[ERROR] Error serving static file {path}: {str(e)}")
        return f"Error serving static file: {str(e)}", 500

# ============================================================================
# API ROUTES - Backend functionality (matching your Vue.js frontend)
# ============================================================================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    backend_files = []
    dist_files = []
    assets_files = []
    
    try:
        backend_files = os.listdir('/usr/src/app/backend/')
    except Exception as e:
        backend_files = [f"Error: {str(e)}"]
    
    try:
        if os.path.exists(STATIC_DIR):
            dist_files = os.listdir(STATIC_DIR)
    except Exception as e:
        dist_files = [f"Error: {str(e)}"]
        
    try:
        assets_dir = os.path.join(STATIC_DIR, 'assets')
        if os.path.exists(assets_dir):
            assets_files = os.listdir(assets_dir)
    except Exception as e:
        assets_files = [f"Error: {str(e)}"]
    
    return jsonify({
        'status': 'healthy',
        'frontend_available': os.path.exists(os.path.join(STATIC_DIR, 'index.html')),
        'static_dir': STATIC_DIR,
        'backend_files': backend_files,
        'dist_files': dist_files,
        'assets_files': assets_files,
        'working_directory': os.getcwd()
    })

@app.route('/api/config')
def get_config():
    """Get current configuration (excluding sensitive data)"""
    options = get_options()
    # Don't expose API keys
    safe_config = {k: ('***' if 'key' in k.lower() and v else v) for k, v in options.items()}
    return jsonify(safe_config)

@app.route('/api/generate_automation', methods=['POST'])
def generate_automation():
    """Generate automation using selected LLM provider (matches your Vue.js frontend)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        options = get_options()
        llm_provider = options.get('llm_provider', 'ollama')
        
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
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
    """Install automation into Home Assistant (matches your Vue.js frontend)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        automation_yaml = data.get('automation_yaml', '')
        if not automation_yaml:
            return jsonify({'error': 'No automation YAML provided'}), 400
        
        print(f"[INFO] Installing automation: {automation_yaml[:200]}...")
        
        # TODO: Implement actual Home Assistant API integration
        # For now, just return success
        return jsonify({
            'success': True,
            'message': 'Automation would be installed (not implemented yet)',
            'automation_yaml': automation_yaml
        })
        
    except Exception as e:
        print(f"[ERROR] Error in install_automation: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_with_ollama(prompt, options):
    """Generate automation using Ollama"""
    try:
        ollama_url = options.get('ollama_api_url', 'http://ollama:11434/api/generate')
        model = options.get('ollama_model', 'llama3')
        
        automation_prompt = f"""Create a detailed Home Assistant automation for the following request:
{prompt}

Please provide:
1. A clear summary of what the automation does
2. The complete YAML configuration

Format your response as JSON with 'summary' and 'yaml' fields."""
        
        payload = {
            'model': model,
            'prompt': automation_prompt,
            'stream': False
        }
        
        print(f"[INFO] Calling Ollama at {ollama_url}")
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        automation_text = result.get('response', '')
        
        # Try to parse as JSON, fallback to text parsing
        try:
            import json
            automation_data = json.loads(automation_text)
            return jsonify(automation_data)
        except:
            # Fallback: create structure from text
            return jsonify({
                'summary': f'Generated automation for: {prompt}',
                'yaml': automation_text
            })
        
    except Exception as e:
        print(f"[ERROR] Ollama error: {str(e)}")
        return jsonify({'error': f'Ollama error: {str(e)}'}), 500

def generate_with_gemini(prompt, options):
    """Generate automation using Google Gemini"""
    try:
        api_key = options.get('gemini_api_key', '')
        if not api_key:
            return jsonify({'error': 'Gemini API key not configured'}), 400
        
        # Updated model name - Google changed from gemini-pro to gemini-1.5-flash or gemini-1.5-pro
        model_name = options.get('gemini_model', 'gemini-1.5-flash')
        
        # Map old model names to new ones
        model_mapping = {
            'gemini-pro': 'gemini-1.5-pro',
            'gemini-pro-vision': 'gemini-1.5-pro',
            'gemini-1.0-pro': 'gemini-1.5-pro'
        }
        
        if model_name in model_mapping:
            model_name = model_mapping[model_name]
            print(f"[INFO] Mapped old model name to: {model_name}")
        
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
        
        # Try to parse as JSON, fallback to text parsing
        try:
            # Clean up the response text to extract JSON
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            automation_data = json.loads(response_text)
            return jsonify(automation_data)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse Gemini JSON response: {e}")
            print(f"[ERROR] Raw response: {response.text}")
            # Fallback: create structure from text
            return jsonify({
                'summary': f'Generated automation for: {prompt}',
                'yaml': response.text
            })
        
    except Exception as e:
        print(f"[ERROR] Gemini error: {str(e)}")
        return jsonify({'error': f'Gemini error: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting AItomations Flask backend...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🎨 Static directory: {STATIC_DIR}")
    print(f"📁 Static files available: {os.path.exists(STATIC_DIR)}")
    
    if os.path.exists(STATIC_DIR):
        print(f"📋 Files in dist: {os.listdir(STATIC_DIR)}")
        assets_dir = os.path.join(STATIC_DIR, 'assets')
        if os.path.exists(assets_dir):
            print(f"📋 Files in assets: {os.listdir(assets_dir)}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8099, debug=False)
