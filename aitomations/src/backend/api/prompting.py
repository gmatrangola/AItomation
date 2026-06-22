from __future__ import annotations

import json
import os
from typing import Any

from flask import current_app
from jinja2 import Environment, FileSystemLoader, TemplateError

from api.config import PROMPTS_DIR
from api.options import get_options  # <-- change from api.routes to api.options

jinja_env = Environment(loader=FileSystemLoader(PROMPTS_DIR), autoescape=False)


_prompts_dir_logged = False


def _log_prompts_dir() -> None:
    """Log prompts directory info - only called when needed."""
    global _prompts_dir_logged
    if _prompts_dir_logged:
        return

    current_app.logger.info("📂 PROMPTS_DIR resolved to: %s", PROMPTS_DIR)
    current_app.logger.info("📂 Directory exists: %s", os.path.exists(PROMPTS_DIR))
    if os.path.exists(PROMPTS_DIR):
        current_app.logger.info("📂 Files in directory: %s", os.listdir(PROMPTS_DIR))
    else:
        current_app.logger.warning("⚠️  PROMPTS_DIR does not exist!")
        abs_path = os.path.abspath(PROMPTS_DIR)
        current_app.logger.warning("⚠️  Absolute path: %s", abs_path)
        parent_dir = os.path.dirname(PROMPTS_DIR)
        if os.path.exists(parent_dir):
            current_app.logger.info("📂 Parent directory contents: %s", os.listdir(parent_dir))
    _prompts_dir_logged = True


def render_system_prompt(
    ha_context: dict[str, Any],
    user_request: str,
    chat_history: list[dict[str, Any]] | None = None,
    docs_reference: str = "",
) -> str:
    """Render the system prompt using the configured Jinja2 template."""
    _log_prompts_dir()

    options = get_options()
    custom_template = (options.get("system_prompt_template") or "").strip()
    chat_history = chat_history or []

    try:
        if custom_template:
            current_app.logger.info("📝 Using custom system prompt template from options")
            template = jinja_env.from_string(custom_template)
        else:
            current_app.logger.info("📝 Using default_system_prompt.jinja2")
            template = jinja_env.get_template("default_system_prompt.jinja2")

        rendered = template.render(
            ha_context=ha_context,
            user_request=user_request,
            chat_history=chat_history,
            docs_reference=docs_reference,
        )

        current_app.logger.debug("=== Rendered system prompt start ===")
        current_app.logger.debug(rendered)
        current_app.logger.debug("=== Rendered system prompt end ===")
        current_app.logger.info("📊 Prompt length: %s characters", len(rendered))

        return rendered
    except TemplateError as exc:
        current_app.logger.error("❌ Template rendering error: %s", exc, exc_info=True)
        # Fallback: minimal but safe prompt
        return (
            "You are a Home Assistant automation assistant.\n\n"
            f"Context: {json.dumps(ha_context, indent=2)}\n\n"
            f"Chat History: {json.dumps(chat_history, indent=2)}\n\n"
            f"User Request: {user_request}\n\n"
            "Generate a YAML automation with an explanation."
        )
