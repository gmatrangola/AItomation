from __future__ import annotations

import os

# Home Assistant Core API
HA_API_URL = "http://supervisor/core/api"

# Home Assistant Core WebSocket API (used for Lovelace/dashboards, which have no REST API)
HA_WS_URL = "ws://supervisor/core/websocket"

# Supervisor token is injected into the container env
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")

HA_HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

# Persistent data directory — /data inside the HA container, overridable for local dev
DATA_DIR = os.environ.get("AITOMATIONS_DATA_DIR", "/data")

# Options file managed by Supervisor
OPTIONS_FILE = os.path.join(DATA_DIR, "options.json")

# Add-on state file we own
ADDON_STATE_FILE = os.path.join(DATA_DIR, "aitomations_config.json")

# Where prompt templates live
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
