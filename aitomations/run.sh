#!/usr/bin/with-contenv bash

# Set the path to the Python script
PYTHON_APP_DIR="/usr/src/app/backend"

# Set the port for the Flask app (must match config.json)
FLASK_PORT=8099

# Change to the backend directory
cd "$PYTHON_APP_DIR" || exit 1

# Start the Flask application using Gunicorn
exec gunicorn \
    --bind 0.0.0.0:"$FLASK_PORT" \
    --workers 1 \
    --log-level info \
    --access-logfile '-' \
    --error-logfile '-' \
    app:app