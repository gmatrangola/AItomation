#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AItomations Creator..."

# Read timeout from addon config (defaults to 120 seconds)
TIMEOUT=$(bashio::config 'request_timeout' '120')

bashio::log.info "Request timeout set to: ${TIMEOUT}s"

cd /usr/src/app

# Start gunicorn with configurable timeout
# Changed from src.backend.main:app to src.backend.app:app
exec gunicorn \
    --bind 0.0.0.0:8099 \
    --workers 2 \
    --timeout ${TIMEOUT} \
    --graceful-timeout ${TIMEOUT} \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    src.backend.app:app