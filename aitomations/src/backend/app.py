import os
import sys
import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# +++ ENSURE PROPER PYTHON PATH +++
# Add the application root to Python path
app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if app_root not in sys.path:
    sys.path.insert(0, app_root)
print(f"[STARTUP] Python path: {sys.path}")
print(f"[STARTUP] Current working directory: {os.getcwd()}")
print(f"[STARTUP] __file__ is: {__file__}")

# +++ START DIAGNOSTIC LOGGING +++
log_file = '/data/aitomations_startup.log'
if os.path.exists(log_file):
    os.remove(log_file)

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("=== app.py module execution started ===")
logging.info(f"Python path: {sys.path}")
logging.info(f"Working directory: {os.getcwd()}")
logging.info(f"__file__: {__file__}")
# +++ END DIAGNOSTIC LOGGING +++

# Import the routes module with multiple strategies
api_blueprint = None

# Strategy 1: Try absolute import from src.backend
try:
    logging.info("Attempting absolute import: from src.backend.api.routes import api_blueprint")
    from src.backend.api.routes import api_blueprint
    logging.info("✓ SUCCESS: Imported via src.backend.api.routes")
except ImportError as e:
    logging.error(f"✗ FAILED absolute import: {e}", exc_info=True)
    
    # Strategy 2: Try relative import
    try:
        logging.info("Attempting relative import: from .api.routes import api_blueprint")
        from .api.routes import api_blueprint
        logging.info("✓ SUCCESS: Imported via relative import")
    except ImportError as e2:
        logging.error(f"✗ FAILED relative import: {e2}", exc_info=True)
        
        # Strategy 3: Try direct module import after adjusting path
        try:
            logging.info("Attempting direct import after path adjustment")
            backend_dir = os.path.dirname(__file__)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
                logging.info(f"Added to path: {backend_dir}")
            
            from api.routes import api_blueprint
            logging.info("✓ SUCCESS: Imported via direct path adjustment")
        except ImportError as e3:
            logging.error(f"✗ FAILED all import strategies: {e3}", exc_info=True)
            logging.error("Routes will NOT be available!")

# --- Application Setup ---
app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)
logging.info("Flask app object created")

# Register the API blueprint
if api_blueprint:
    try:
        app.register_blueprint(api_blueprint, url_prefix='/api')
        logging.info("✓ API blueprint registered successfully with url_prefix='/api'")
        
        # Log all registered routes
        logging.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            logging.info(f"  [{methods}] {rule.rule} -> {rule.endpoint}")
            
        # Count API routes
        api_routes = [r for r in app.url_map.iter_rules() if r.rule.startswith('/api/')]
        logging.info(f"Total API routes registered: {len(api_routes)}")
        
    except Exception as e:
        logging.error(f"✗ FAILED to register blueprint: {e}", exc_info=True)
else:
    logging.error("✗ CRITICAL: api_blueprint is None! Routes NOT registered!")
    logging.error("The application will start but API endpoints will not work.")

# --- Debug Routes ---
@app.route('/ping')
def ping():
    """Health check endpoint."""
    return jsonify({"message": "pong", "routes_registered": api_blueprint is not None})

@app.route('/debug/routes')
def debug_routes():
    """List all registered routes."""
    routes_list = []
    for rule in app.url_map.iter_rules():
        routes_list.append({
            'endpoint': rule.endpoint,
            'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
            'path': str(rule)
        })
    
    api_routes = [r for r in routes_list if r['path'].startswith('/api/')]
    
    return jsonify({
        'total_routes': len(routes_list),
        'api_routes': len(api_routes),
        'blueprint_loaded': api_blueprint is not None,
        'routes': sorted(routes_list, key=lambda x: x['path'])
    })

@app.route('/debug/startup-log')
def debug_startup_log():
    """View the startup log."""
    try:
        with open('/data/aitomations_startup.log', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        return "Startup log not found", 404

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    """Serve the Vue.js application."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# --- Development Server ---
if __name__ == '__main__':
    print("🚀 Starting AItomations Flask backend for development...")
    print(f"API Blueprint loaded: {api_blueprint is not None}")
    app.run(host='0.0.0.0', port=8099, debug=True)