#!/usr/bin/with-contenv bash
# add-on/run.sh

# Set the path to the Python script
PYTHON_APP="/app/backend/app.py"

# Set the port for the Flask app (must match config.json)
FLASK_PORT=8099

# Log startup message
echo "[Info] Starting AItomation add-on..."

# Check if SUPERVISOR_TOKEN is available
if [ -z "$SUPERVISOR_TOKEN" ]; then
    echo "[Error] SUPERVISOR_TOKEN not found. This add-on requires API access."
    exit 1
fi

# Pass add-on options as environment variables to the Python app
# These variables are automatically injected by Home Assistant Supervisor
# based on config.json options.
export OLLAMA_API_URL=$(jq --raw-output ".ollama_api_url // \"\"" /data/options.json)
export OLLAMA_MODEL=$(jq --raw-output ".ollama_model // \"\"" /data/options.json)
export GEMINI_API_KEY=$(jq --raw-output ".gemini_api_key // \"\"" /data/options.json)
export GEMINI_MODEL=$(jq --raw-output ".gemini_model // \"\"" /data/options.json)
export LLM_PROVIDER=$(jq --raw-output ".llm_provider // \"ollama\"" /data/options.json)

echo "[Info] LLM Provider selected: $LLM_PROVIDER"
if [ "$LLM_PROVIDER" == "ollama" ]; then
    echo "[Info] Ollama API URL: $OLLAMA_API_URL"
    echo "[Info] Ollama Model: $OLLAMA_MODEL"
elif [ "$LLM_PROVIDER" == "gemini" ]; then
    echo "[Info] Gemini Model: $GEMINI_MODEL"
    # Do not echo API key for security reasons
fi


# Start the Flask application using Gunicorn
# Gunicorn is a robust WSGI HTTP server suitable for production.
exec gunicorn \
    --bind 0.0.0.0:"$FLASK_PORT" \
    --workers 1 \
    --log-level info \
    --access-logfile '-' \
    --error-logfile '-' \
    "$PYTHON_APP":app # 'app' is the Flask application instance in app.py

echo "[Info] LLM Automation Creator add-on stopped."
