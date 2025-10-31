import json
import os
import re
import time
import traceback

import requests
import yaml
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from api.errors import APIError
from llm.gemini import GeminiProvider
from llm.ollama import OllamaProvider

api_blueprint = Blueprint("api", __name__)

# --- Constants ---
HA_API_URL = "http://supervisor/core/api"
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}
OPTIONS_FILE = "/data/options.json"
AITOMATIONS_METADATA_KEY = "aitomations_metadata"


# --- Helper Functions ---
def get_options():
    try:
        with open(OPTIONS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_llm_provider(provider_name: str):
    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


def _get_ha_context():
    if not SUPERVISOR_TOKEN:
        raise ConnectionError("Supervisor token not found.")
    try:
        states_response = requests.get(f"{HA_API_URL}/states", headers=HA_HEADERS, timeout=10)
        states_response.raise_for_status()
        all_states = states_response.json()
        entities = [
            {"id": e["entity_id"], "name": e["attributes"].get("friendly_name", e["entity_id"])} for e in all_states
        ]
        automations = [
            {"id": s["entity_id"], "name": s["attributes"].get("friendly_name", s["entity_id"])}
            for s in all_states
            if s["entity_id"].startswith("automation.")
        ]
        services_response = requests.get(f"{HA_API_URL}/services", headers=HA_HEADERS, timeout=10)
        services_response.raise_for_status()
        services = [
            f"{domain['domain']}.{service}" for domain in services_response.json() for service in domain["services"]
        ]
        context_data = {"entities": entities, "services": services, "automations": automations}
        summary = f"Context: {len(entities)} entities, {len(services)} services, and {len(automations)} automations."
        return context_data, summary
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Could not connect to Home Assistant API: {e}") from e


# --- API Endpoints ---
@api_blueprint.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


@api_blueprint.route("/config")
def get_config():
    options = get_options()
    safe_config = {k: ("***" if "key" in k.lower() and v else v) for k, v in options.items()}
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
        current_app.logger.error(f" An unexpected error occurred in get_automations: {e}")
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
        current_app.logger.info(f" Loaded {len(messages)} messages from storage")

        return jsonify({"messages": messages})
    except Exception as e:
        current_app.logger.error(f" Error loading chat history: {e}")
        return jsonify({"messages": [], "error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["POST"])
def save_chat_history():
    """Save chat history to Home Assistant storage."""
    try:
        data = request.get_json()
        messages = data.get("messages", [])

        current_app.logger.info(f" Saving {len(messages)} messages to storage")

        storage_path = "/data/chat_history.json"
        storage_data = {"messages": messages, "timestamp": time.time()}

        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        with open(storage_path, "w") as f:
            json.dump(storage_data, f, indent=2)

        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f" Error saving chat history: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["DELETE"])
def clear_chat_history():
    """Clear persisted chat history."""
    try:
        storage_path = "/data/chat_history.json"

        if os.path.exists(storage_path):
            os.remove(storage_path)
            current_app.logger.info(" Chat history cleared")

        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f" Error clearing chat history: {e}")
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
            conversation_history = data.get("conversation_history", [])

            if not prompt:
                error_response = {
                    "type": "error",
                    "error_code": "INVALID_INPUT",
                    "context": {"field": "prompt"},
                }
                yield f"data: {json.dumps(error_response)}\n\n"
                return

            # Build context
            full_context = ""
            if conversation_history:
                full_context = "Previous conversation:\n"
                for msg in conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    full_context += f"{role}: {msg['content']}\n\n"
                full_context += f"User: {prompt}"
            else:
                full_context = prompt

            options = get_options()
            llm_provider_name = options.get("llm_provider", "ollama")

            # Get LLM provider inside try block to catch ValueError from URL parsing
            try:
                llm_provider = get_llm_provider(llm_provider_name)
            except ValueError as e:
                current_app.logger.error(f" Invalid LLM provider configuration: {e}")
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

            # Send initial progress - gathering context
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'gathering_context'})}\n\n"

            ha_context, context_summary = _get_ha_context()

            # Send context statistics
            context_stats = {
                "type": "progress",
                "stage": "context_ready",
                "stats": {
                    "entities": len(ha_context.get("entities", [])),
                    "services": len(ha_context.get("services", [])),
                    "automations": len(ha_context.get("automations", [])),
                    "prompt_length": len(full_context),
                },
            }
            yield f"data: {json.dumps(context_stats)}\n\n"

            creation_prompt = f"""You are an expert Home Assistant automation assistant. Your goal is to generate a single, complete YAML configuration for an automation based on the user's request and the provided context.

**Instructions:**
1.  Analyze the user's request and the available Home Assistant context (entities, services).
2.  Create a valid Home Assistant automation in YAML format.
3.  Your response **MUST** be in Markdown format.
4.  The response should contain two parts:
    - An "Explanation" section that describes what the automation does in simple terms.
    - A "YAML" section containing the automation configuration inside a `yaml` code block.

**Home Assistant Context:**
```json
{json.dumps(ha_context, indent=2)}
```

**User Request:**
{full_context}

Example Response Format:

## Explanation
This automation will turn on the kitchen light when motion is detected.

```yaml
alias: Turn on Kitchen Light on Motion
description: ''
trigger:
  - platform: state
    entity_id: binary_sensor.kitchen_motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen_light
mode: single
```
"""

            # Send generating stage
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'generating', 'provider': llm_provider_name})}\n\n"

            yield f"data: {json.dumps({'type': 'start'})}\n\n"

            full_response = ""
            chunk_count = 0
            for chunk in llm_provider.generate_stream(creation_prompt, options):
                full_response += chunk
                chunk_count += 1

                # Send content with progress metadata every 10 chunks
                if chunk_count % 10 == 0:
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk, 'chunks_received': chunk_count})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

            # Send completion progress
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'complete', 'total_chunks': chunk_count, 'response_length': len(full_response)})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

        except APIError as e:
            # Structured error with error code and context
            current_app.logger.error(f" APIError: {e.code.value} - {e.context}")
            error_response = {"type": "error", **e.to_dict()}
            yield f"data: {json.dumps(error_response)}\n\n"

        except ValueError as e:
            # Handle URL parsing errors and other ValueErrors
            current_app.logger.error(f" ValueError: {e}")
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
            current_app.logger.error(f" Unexpected error: {e}")
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
            options = get_options()
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
        current_app.logger.error(f" Error in install_automation: {str(e)}")
        return jsonify({"error": str(e)}), 500
