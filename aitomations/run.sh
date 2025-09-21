#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AItomations backend server with Gunicorn..."

# Change the working directory to the application root.
# This makes '/usr/src/app' the starting point for Python's module search.
cd /usr/src/app

# The Gunicorn command to run the Flask application.
# The --pythonpath argument is now redundant because of the 'cd' command,
# but we will leave it for maximum compatibility.
exec gunicorn \
    --workers 2 \
    --bind "0.0.0.0:8099" \
    --log-level info \
    --access-logfile '-' \
    --error-logfile '-' \
    --pythonpath /usr/src/app \
    "src.backend.app:app"