import json
import os
import re
import time
import traceback
from typing import Any

import requests
import yaml
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from api.config import (
    ADDON_STATE_FILE,
    HA_API_URL,
    HA_HEADERS,
    PROMPTS_DIR,
    SUPERVISOR_TOKEN,
)
from api.context import get_ha_context
from api.errors import APIError
from api.options import get_options
from api.prompting import render_system_prompt
from llm.gemini import GeminiProvider
from llm.ollama import OllamaProvider

api_blueprint = Blueprint("api", __name__)

# --- Constants ---
AITOMATIONS_METADATA_KEY = "aitomations_metadata"


# --- Helper Functions ---
def get_llm_provider(provider_name: str):
    if provider_name == "gemini":
        return GeminiProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider_name}")


def load_addon_state() -> dict[str, Any]:
    """Load addon-specific persistent state (e.g., API tokens) from our own file."""
    try:
        with open(ADDON_STATE_FILE) as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict):
        return data
    return {}


def save_addon_state(state: dict[str, Any]) -> None:
    """Persist addon-specific state to our own file."""
    os.makedirs(os.path.dirname(ADDON_STATE_FILE), exist_ok=True)
    with open(ADDON_STATE_FILE, "w") as file:
        json.dump(state, file, indent=2)


def get_effective_config() -> dict[str, Any]:
    """Supervisor options overlaid with persisted addon state."""
    base = get_options()
    state = load_addon_state()
    return {**base, **state}


# --- API Endpoints ---
@api_blueprint.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


@api_blueprint.route("/config", methods=["POST"])
def save_config():
    """Save addon configuration (tokens, model prefs) to our own state file."""
    try:
        data = request.get_json() or {}
        current_app.logger.info("🛠 Received config save request: %s", list(data.keys()))

        # Supervisor options (read-only base)
        base_options = get_options()
        # Our persisted state (read/write)
        state = load_addon_state()

        # Start from existing state, then overlay new values
        merged: dict[str, Any] = {**state}

        # Preserve any masked secret fields containing 'key'
        for key, value in list(data.items()):
            if "key" in key.lower() and value == "***":
                # Keep existing real value if present in state
                if state.get(key):
                    merged[key] = state[key]
                else:
                    merged[key] = ""
            else:
                merged[key] = value

        # Effective config for validation (state over base options)
        effective = {**base_options, **merged}
        llm_provider = effective.get("llm_provider")

        if llm_provider not in ("gemini", "ollama"):
            current_app.logger.warning("⚠️ Invalid LLM provider in config: %r", llm_provider)
            return (
                jsonify({"success": False, "error": "Invalid LLM provider", "details": {"llm_provider": llm_provider}}),
                400,
            )

        save_addon_state(merged)
        current_app.logger.info("✅ Add-on configuration saved successfully")
        return jsonify({"success": True})
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error("❌ Error saving configuration", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@api_blueprint.route("/config")
def get_config():
    # Base options from Supervisor + addon-specific state
    base_options = get_options()
    state = load_addon_state()

    # State overrides base options where keys overlap
    effective: dict[str, Any] = {**base_options, **state}

    safe_config: dict[str, object] = {}
    for k, v in effective.items():
        if "key" in k.lower() and v:
            safe_config[k] = "***"
            safe_config[f"{k}_present"] = True
        else:
            safe_config[k] = v
    return jsonify(safe_config)


@api_blueprint.route("/automations")
def get_automations():
    if not SUPERVISOR_TOKEN:
        return jsonify({"error": "Supervisor token not found"}), 500
    try:
        states_response = requests.get(f"{HA_API_URL}/states", headers=HA_HEADERS, timeout=15)
        states_response.raise_for_status()
        automation_entities = [s for s in states_response.json() if s["entity_id"].startswith("automation.")]

        processed_automations = []
        for entity in automation_entities:
            entity_id = entity["entity_id"]
            automation_id = entity_id.split(".", 1)[1]
            config_response = requests.get(
                f"{HA_API_URL}/config/automation/config/{automation_id}", headers=HA_HEADERS, timeout=10
            )

            item = {
                "id": automation_id,
                "entity_id": entity_id,
                "alias": entity["attributes"].get("friendly_name", automation_id.replace("_", " ").title()),
                "state": entity["state"],
                "prompt": None,
                "source": None,
                "is_editable": False,
            }

            if config_response.status_code == 200:
                config = config_response.json()
                metadata = config.get(AITOMATIONS_METADATA_KEY, {})
                item.update(
                    {
                        "id": config.get("id", automation_id),
                        "alias": config.get("alias", item["alias"]),
                        "prompt": metadata.get("prompt"),
                        "source": metadata.get("source"),
                        "is_editable": True,
                    }
                )
            processed_automations.append(item)
        return jsonify(processed_automations)
    except Exception as e:
        current_app.logger.error(f"❌ An unexpected error occurred in get_automations: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


# Chat history endpoints
@api_blueprint.route("/chat/history", methods=["GET"])
def get_chat_history():
    """Get persisted chat history from Home Assistant storage."""
    try:
        storage_path = "/data/chat_history.json"

        if not os.path.exists(storage_path):
            return jsonify({"messages": []})

        with open(storage_path) as f:
            data = json.load(f)

        # Check if data is too old (7 days)
        timestamp = data.get("timestamp", 0)
        age_days = (time.time() - timestamp) / (60 * 60 * 24)

        if age_days > 7:
            os.remove(storage_path)
            return jsonify({"messages": []})

        messages = data.get("messages", [])
        current_app.logger.info(f"📚 Loaded {len(messages)} messages from storage")

        return jsonify({"messages": messages})
    except Exception as e:
        current_app.logger.error(f"❌ Error loading chat history: {e}")
        return jsonify({"messages": [], "error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["POST"])
def save_chat_history():
    """Save chat history to Home Assistant storage."""
    try:
        data = request.get_json()
        messages = data.get("messages", [])

        current_app.logger.info(f"💾 Saving {len(messages)} messages to storage")

        storage_path = "/data/chat_history.json"
        storage_data = {"messages": messages, "timestamp": time.time()}

        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        with open(storage_path, "w") as f:
            json.dump(storage_data, f, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f"❌ Error saving chat history: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["DELETE"])
def clear_chat_history():
    """Clear persisted chat history."""
    try:
        storage_path = "/data/chat_history.json"

        if os.path.exists(storage_path):
            os.remove(storage_path)
            current_app.logger.info("🗑️  Chat history cleared")

        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f"❌ Error clearing chat history: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/generate_automation/stream", methods=["POST"])
def generate_automation_stream():
    """Generate automation with streaming response via Server-Sent Events."""

    def generate():
        try:
            yield ": connected\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'initializing_context'})}\n\n"
            data = request.get_json()

            prompt = data.get("prompt")
            conversation_history = data.get("conversation_history", []) or []

            current_app.logger.info(f"💬 New generation request - Prompt: {prompt[:100]}...")
            if conversation_history:
                current_app.logger.info(f"📜 Conversation history (raw): {len(conversation_history)} messages")

            if not prompt:
                error_response = {
                    "type": "error",
                    "error_code": "INVALID_INPUT",
                    "context": {"field": "prompt"},
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                return

            options = get_effective_config()
            llm_provider_name = options.get("llm_provider", "ollama")

            # --- NEW: limit number of chat messages sent as context ---
            try:
                max_history = int(options.get("chat_history_max_messages", 10))
            except (ValueError, TypeError):
                max_history = 10

            if max_history > 0 and conversation_history:
                trimmed_history = conversation_history[-max_history:]
            else:
                trimmed_history = []

            current_app.logger.info(
                f"🧠 Using {len(trimmed_history)}/{len(conversation_history)} history messages for context "
                f"(max_history={max_history})"
            )

            # Build a text version of the (trimmed) history for models that
            # benefit from a flattened conversation string.
            history_text = ""
            for msg in trimmed_history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n\n"

            # full_context stays small: just the current user prompt plus optional header
            if trimmed_history:
                full_context = f"User: {prompt}"
            else:
                full_context = prompt

            try:
                llm_provider = get_llm_provider(llm_provider_name)
            except ValueError as e:
                current_app.logger.error(f"❌ Invalid LLM provider configuration: {e}")
                error_response = {
                    "type": "error",
                    "error_code": "INVALID_CONFIG",
                    "context": {
                        "details": str(e),
                        "provider": llm_provider_name,
                    },
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'progress', 'stage': 'gathering_context'})}\n\n"

            ha_context, context_summary = get_ha_context()

            context_stats = {
                "type": "progress",
                "stage": "context_ready",
                "stats": {
                    "entities": len(ha_context.get("entities", [])),
                    "services": len(ha_context.get("services", [])),
                    "automations": len(ha_context.get("automations", [])),
                    "prompt_length": len(full_context) + len(history_text),
                    "history_messages": len(trimmed_history),
                },
            }
            yield f"data: {json.dumps(context_stats)}\n\n"

            current_app.logger.info("🔨 Rendering system prompt from template...")
            creation_prompt = render_system_prompt(
                ha_context=ha_context,
                user_request=full_context,
                chat_history=trimmed_history,
            )

            yield f"data: {json.dumps({'type': 'progress', 'stage': 'generating', 'provider': llm_provider_name})}\n\n"

            yield f"data: {json.dumps({'type': 'start'})}\n\n"

            full_response = ""
            chunk_count = 0
            for chunk in llm_provider.generate_stream(creation_prompt, options):
                full_response += chunk
                chunk_count += 1

                if chunk_count % 10 == 0:
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk, 'chunks_received': chunk_count})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

            current_app.logger.info(f"✅ Generation complete - {chunk_count} chunks, {len(full_response)} characters")

            yield f"data: {json.dumps({'type': 'progress', 'stage': 'complete', 'total_chunks': chunk_count, 'response_length': len(full_response)})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

        except APIError as e:
            # Structured error with error code and context
            current_app.logger.error(f"❌ APIError: {e.code.value} - {e.context}")
            error_response = {"type": "error", **e.to_dict()}
            yield f"data: {json.dumps(error_response)}\n\n"

        except ValueError as e:
            # Handle URL parsing errors and other ValueErrors
            current_app.logger.error(f"❌ ValueError: {e}")
            error_response = {
                "type": "error",
                "error_code": "INVALID_CONFIG",
                "context": {
                    "details": str(e),
                    "provider": options.get("llm_provider", "ollama") if "options" in locals() else "unknown",
                },
            }
            yield f"data: {json.dumps(error_response)}\n\n"

        except Exception as e:
            # Unexpected error
            current_app.logger.error(f"❌ Unexpected error: {e}")
            traceback.print_exc()

            error_response = {
                "type": "error",
                "error_code": "UNKNOWN_ERROR",
                "context": {"details": str(e)},
            }
            yield f"data: {json.dumps(error_response)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@api_blueprint.route("/install_automation", methods=["POST"])
def install_automation():
    try:
        data = request.get_json()
        automation_yaml = data["automation_yaml"]
        prompt = data.get("prompt")

        config = yaml.safe_load(automation_yaml)
        if isinstance(config, list):
            config = config[0]

        if prompt:
            options = get_effective_config()
            config[AITOMATIONS_METADATA_KEY] = {
                "source": "aitomations_addon",
                "prompt": prompt,
                "llm_provider": options.get("llm_provider"),
                "model": options.get("gemini_model")
                if options.get("llm_provider") == "gemini"
                else options.get("ollama_model"),
                "timestamp": int(time.time()),
            }

        if "id" not in config or not config["id"]:
            alias = config.get("alias", "New AItomation")
            slug = re.sub(r"[^\w-]", "", re.sub(r"\s+", "_", alias).lower())
            config["id"] = f"{slug}_{int(time.time())}"

        install_url = f"http://supervisor/core/api/config/automation/config/{config['id']}"
        response = requests.post(install_url, headers=HA_HEADERS, json=config, timeout=15)
        response.raise_for_status()

        return jsonify(response.json())
    except Exception as e:
        current_app.logger.error(f"❌ Error in install_automation: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/default_prompt_template")
def get_default_prompt_template():
    """Get the default system prompt template."""
    try:
        template_path = os.path.join(PROMPTS_DIR, "default_system_prompt.jinja2")
        if os.path.exists(template_path):
            with open(template_path) as f:
                return jsonify({"template": f.read()})
        else:
            return jsonify({"error": "Default template not found"}), 404
    except Exception as e:
        current_app.logger.error(f"❌ Error reading default template: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/preview_prompt_template", methods=["POST"])
def preview_prompt_template():
    """Preview a template with real Home Assistant data."""
    try:
        data = request.get_json()
        template_str = data.get("template", "")

        if not template_str:
            return jsonify({"error": "No template provided"}), 400

        try:
            ha_context, _ = get_ha_context()
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"Failed to fetch Home Assistant data: {exc}"}), 500

        sample_request = "Turn on the living room lights when motion is detected after sunset"
        sample_history: list[dict[str, Any]] = []

        from jinja2 import Template

        template = Template(template_str)
        rendered = template.render(
            ha_context=ha_context,
            user_request=sample_request,
            chat_history=sample_history,
        )

        return jsonify({"rendered": rendered})
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(f"❌ Error previewing template: {exc}")
        return jsonify({"error": str(exc)}), 500
