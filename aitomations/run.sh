#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AItomations Creator..."

# Read timeout from addon config (defaults to 120 seconds)
TIMEOUT=$(bashio::config 'request_timeout' '120')

bashio::log.info "Request timeout set to: ${TIMEOUT}s"

cd /usr/src/app

# Start gunicorn with gthread worker for better streaming support
exec gunicorn \
    --bind 0.0.0.0:8099 \
    --worker-class gthread \
    --workers 2 \
    --threads 4 \
    --timeout ${TIMEOUT} \
    --graceful-timeout ${TIMEOUT} \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output \
    --enable-stdio-inheritance \
    src.backend.app:app