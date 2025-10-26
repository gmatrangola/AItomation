import logging
import os
import sys

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# +++ ENSURE PROPER PYTHON PATH +++
app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

# +++ CREATE FLASK APP FIRST (so app.logger is available) +++
app = Flask(__name__, static_folder="dist", static_url_path="/")
CORS(app)

# Set log level for the Flask app logger (used by Gunicorn)
app.logger.setLevel(logging.DEBUG)

app.logger.info("=== app.py module execution started ===")
app.logger.info(f"Python path: {sys.path}")
app.logger.info(f"Working directory: {os.getcwd()}")
app.logger.info(f"__file__: {__file__}")

# Import the routes module
api_blueprint: object | None = None

backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from api.routes import api_blueprint  # type: ignore[import-not-found]

    app.logger.info("✓ SUCCESS: Imported api_blueprint")
except ImportError as e:
    app.logger.error(f"✗ FAILED to import api_blueprint: {e}", exc_info=True)
    app.logger.error("Routes will NOT be available!")

# Register the API blueprint
if api_blueprint:
    try:
        app.register_blueprint(api_blueprint, url_prefix="/api")  # type: ignore[arg-type]
        app.logger.info("✓ API blueprint registered successfully with url_prefix='/api'")

        # Log all registered routes
        app.logger.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            app.logger.info(f"  [{methods}] {rule.rule} -> {rule.endpoint}")

        api_routes = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/")]
        app.logger.info(f"Total API routes registered: {len(api_routes)}")

    except Exception as e:
        app.logger.error(f"✗ FAILED to register blueprint: {e}", exc_info=True)
else:
    app.logger.error("✗ CRITICAL: api_blueprint is None! Routes NOT registered!")
    app.logger.error("The application will start but API endpoints will not work.")


# --- Debug Routes ---
@app.route("/ping")
def ping():
    """Health check endpoint."""
    return jsonify({"message": "pong", "routes_registered": api_blueprint is not None})


@app.route("/debug/routes")
def debug_routes():
    """List all registered routes."""
    routes_list = []
    for rule in app.url_map.iter_rules():
        methods = rule.methods or set()
        routes_list.append(
            {"endpoint": rule.endpoint, "methods": sorted(methods - {"HEAD", "OPTIONS"}), "path": str(rule)}
        )

    api_routes = [r for r in routes_list if r["path"].startswith("/api/")]

    return jsonify(
        {
            "total_routes": len(routes_list),
            "api_routes": len(api_routes),
            "blueprint_loaded": api_blueprint is not None,
            "routes": sorted(routes_list, key=lambda x: x["path"]),
        }
    )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue_app(path: str):
    """Serve the Vue.js application."""
    static_folder = app.static_folder or "dist"
    if path != "" and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    else:
        return send_from_directory(static_folder, "index.html")


# --- Development Server ---
if __name__ == "__main__":
    print("🚀 Starting AItomations Flask backend for development...")
    print(f"API Blueprint loaded: {api_blueprint is not None}")
    app.run(host="0.0.0.0", port=8099, debug=True)
