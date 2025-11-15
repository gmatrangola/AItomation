from __future__ import annotations

import os

# Home Assistant Core API
HA_API_URL = "http://supervisor/core/api"

# Supervisor token is injected into the container env
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")

HA_HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

# Options file managed by Supervisor
OPTIONS_FILE = "/data/options.json"

# Add-on state file we own
ADDON_STATE_FILE = "/data/aitomations_config.json"

# Where prompt templates live
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
