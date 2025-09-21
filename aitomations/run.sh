#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AItomations backend server with Gunicorn..."

# The Gunicorn command to run the Flask application.
# --pythonpath /usr/src/app: This directly tells Gunicorn to add /usr/src/app
# to Python's import path, solving the "No module named 'src'" issue.
exec gunicorn \
    --workers 2 \
    --bind "0.0.0.0:8099" \
    --log-level info \
    --access-logfile '-' \
    --error-logfile '-' \
    --pythonpath /usr/src/app \
    "src.backend.app:app"