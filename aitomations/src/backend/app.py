import os
from flask import Flask, send_from_directory
from flask_cors import CORS

# Import the routes module directly
from .api import routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='dist', static_url_path='/')
    CORS(app)

    # Register the API blueprint directly from the imported routes module
    app.register_blueprint(routes.api_blueprint, url_prefix='/api')

    # --- FRONTEND SERVING ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_vue_app(path):
        """Serve the Vue.js application."""
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    return app

# This is the 'app' object that Gunicorn will look for
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting AItomations Flask backend for development...")
    app.run(host='0.0.0.0', port=8099, debug=True)