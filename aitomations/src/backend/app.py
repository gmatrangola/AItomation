import os
import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# +++ START NEW DIAGNOSTIC LOGGING +++
# Set up logging to a file in the persistent /data directory.
# This will tell us if this module is ever executed by the Gunicorn worker.
log_file = '/data/aitomations_startup.log'
# Clear the log file on each startup for a clean slate.
if os.path.exists(log_file):
    os.remove(log_file)

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("--- app.py module execution started ---")
# +++ END NEW DIAGNOSTIC LOGGING +++

# Import the routes module directly
try:
    from .api import routes
    logging.info("Successfully imported 'routes' module.")
except Exception as e:
    logging.error(f"Failed to import 'routes' module: {e}", exc_info=True)
    routes = None # Ensure routes is defined

# --- Application Setup (No Factory) ---
# Create and configure the Flask app directly at the module level.
app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)
logging.info("Flask app object created.")

# Register the API blueprint directly onto the app object.
if routes:
    try:
        app.register_blueprint(routes.api_blueprint, url_prefix='/api')
        logging.info("Successfully registered API blueprint.")
    except Exception as e:
        logging.error(f"Failed to register blueprint: {e}", exc_info=True)
else:
    logging.warning("'routes' module not available. Skipping blueprint registration.")

# Log the final URL map
logging.debug(f"Final URL Map: {app.url_map}")


# --- Debug and Frontend Routes ---
@app.route('/ping')
def ping():
    """A simple debug route to confirm the app is running and routing."""
    return jsonify({"message": "pong"})

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
    # The app object is already created, so we just run it.
    app.run(host='0.0.0.0', port=8099, debug=True)