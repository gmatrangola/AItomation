from __future__ import annotations

import json
from typing import Any

from api.config import OPTIONS_FILE


def get_options() -> dict[str, Any]:
    """Load Supervisor-provided add-on options from /data/options.json."""
    try:
        with open(OPTIONS_FILE) as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict):
        return data
    return {}
