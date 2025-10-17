import json
import os
import re
import time

import requests
import yaml
from flask import Blueprint, Response, jsonify, request, stream_with_context

# These imports were missing from the previous version
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
        print(f"[ERROR] An unexpected error occurred in get_automations: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


# Chat history endpoints
@api_blueprint.route("/chat/history", methods=["GET"])
def get_chat_history():
    """Get persisted chat history from Home Assistant storage."""
    print("[INFO] get_chat_history called")
    try:
        storage_path = "/data/chat_history.json"

        if not os.path.exists(storage_path):
            print("[INFO] No chat history found")
            return jsonify({"messages": []})

        with open(storage_path) as f:
            data = json.load(f)

        # Check if data is too old (7 days)
        timestamp = data.get("timestamp", 0)
        age_days = (time.time() - timestamp) / (60 * 60 * 24)

        if age_days > 7:
            print(f"[INFO] Chat history is {age_days:.1f} days old, clearing")
            os.remove(storage_path)
            return jsonify({"messages": []})

        messages = data.get("messages", [])
        print(f"[INFO] Loaded {len(messages)} messages from storage")

        return jsonify({"messages": messages})
    except Exception as e:
        print(f"[ERROR] Error loading chat history: {e}")
        return jsonify({"messages": [], "error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["POST"])
def save_chat_history():
    """Save chat history to Home Assistant storage."""
    print("[INFO] save_chat_history called")
    try:
        data = request.get_json()
        messages = data.get("messages", [])

        print(f"[INFO] Saving {len(messages)} messages to storage")

        storage_path = "/data/chat_history.json"
        storage_data = {"messages": messages, "timestamp": time.time()}

        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        with open(storage_path, "w") as f:
            json.dump(storage_data, f, indent=2)

        print("[INFO] Chat history saved successfully")
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Error saving chat history: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/chat/history", methods=["DELETE"])
def clear_chat_history():
    """Clear persisted chat history."""
    print("[INFO] clear_chat_history called")
    try:
        storage_path = "/data/chat_history.json"

        if os.path.exists(storage_path):
            os.remove(storage_path)
            print("[INFO] Chat history cleared")

        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Error clearing chat history: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/generate_automation/stream", methods=["POST"])
def generate_automation_stream():
    """Generate automation with streaming response."""
    print("[INFO] /api/generate_automation/stream endpoint called")

    def generate():
        try:
            data = request.get_json()
            prompt = data.get("prompt")
            conversation_history = data.get("conversation_history", [])

            print(f"[INFO] Prompt: {prompt}")
            print(f"[INFO] Conversation history length: {len(conversation_history)}")

            if not prompt:
                yield f"data: {json.dumps({'type': 'error', 'error': 'No prompt provided'})}\n\n"
                return

            # Build full context with conversation history
            full_context = ""
            if conversation_history:
                print("[INFO] Building context from conversation history")
                full_context = "Previous conversation:\n"
                for i, msg in enumerate(conversation_history):
                    role = "User" if msg["role"] == "user" else "Assistant"
                    full_context += f"{role}: {msg['content']}\n\n"
                    print(f"[DEBUG] History message {i}: {role}")
                full_context += f"User: {prompt}"
            else:
                print("[INFO] No conversation history, using prompt directly")
                full_context = prompt

            print(f"[INFO] Full context length: {len(full_context)} characters")

            options = get_options()
            llm_provider_name = options.get("llm_provider", "ollama")
            print(f"[INFO] Using LLM provider: {llm_provider_name}")
            llm_provider = get_llm_provider(llm_provider_name)

            ha_context, context_summary = _get_ha_context()

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

            print(f"[DEBUG] Full prompt sent to LLM:\n---\n{creation_prompt}\n---")

            # Generate response from LLM
            llm_response = llm_provider.generate(creation_prompt, options)
            full_response = llm_response.get("full_response", "")

            print(f"[INFO] LLM response received, length: {len(full_response)}")

            # Stream the response in chunks
            chunk_size = 50
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i : i + chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"
            print("[INFO] Streaming complete")

        except (ConnectionError, TimeoutError, RuntimeError) as e:
            # These are our custom errors with formatted messages
            print(f"[ERROR] Error in generate_automation_stream: {e}")
            error_message = str(e)  # Already formatted with markdown
            yield f"data: {json.dumps({'type': 'error', 'error': error_message})}\n\n"
        except Exception as e:
            print(f"[ERROR] Unexpected error in generate_automation_stream: {e}")
            import traceback

            traceback.print_exc()

            # Format unexpected errors nicely too
            error_message = (
                f"❌ An unexpected error occurred\n\n"
                f"**Error type:** {type(e).__name__}\n\n"
                f"**Details:** {str(e)}\n\n"
                f"Please check the add-on logs for more information."
            )
            yield f"data: {json.dumps({'type': 'error', 'error': error_message})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_blueprint.route("/generate_automation", methods=["POST"])
def generate_automation():
    print("[INFO] /api/generate_automation endpoint called.")
    try:
        data = request.get_json()
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "A non-empty prompt is required"}), 400

        options = get_options()
        llm_provider_name = options.get("llm_provider", "ollama")
        print(f"[INFO] Using LLM provider: {llm_provider_name}")
        llm_provider = get_llm_provider(llm_provider_name)

        ha_context, context_summary = _get_ha_context()

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
{prompt}

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
        print(f"[DEBUG] Full prompt sent to LLM:\n---\n{creation_prompt}\n---")

        llm_response = llm_provider.generate(creation_prompt, options)
        llm_response["context_summary"] = context_summary
        llm_response["prompt"] = prompt
        return jsonify(llm_response)
    except Exception as e:
        print(f"[ERROR] An exception occurred in generate_automation: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500


@api_blueprint.route("/edit_automation", methods=["POST"])
def edit_automation():
    try:
        data = request.get_json()
        if not all(k in data for k in ["automation_id", "prompt"]):
            return jsonify({"error": "automation_id and prompt are required"}), 400

        config_response = requests.get(
            f"{HA_API_URL}/config/automation/config/{data['automation_id']}", headers=HA_HEADERS
        )
        config_response.raise_for_status()
        existing_config = config_response.json()

        if AITOMATIONS_METADATA_KEY in existing_config:
            del existing_config[AITOMATIONS_METADATA_KEY]
        existing_yaml = yaml.dump(existing_config)

        ha_context, context_summary = _get_ha_context()
        options = get_options()
        llm_provider = get_llm_provider(options.get("llm_provider", "ollama"))

        edit_prompt = f"""You are an expert Home Assistant automation editor. Your goal is to modify an existing automation's YAML based on a user's request.

**Instructions:**
1.  Analyze the user's modification request and the existing YAML.
2.  Generate the **complete, new** YAML for the modified automation.
3.  Your response **MUST** be in Markdown format.
4.  The response should contain two parts:
    - An "Explanation" section that describes the changes you made.
    - A "YAML" section containing the **full** modified automation configuration inside a `yaml` code block.

**Existing Automation YAML:**
```yaml
{existing_yaml}
```

**User's Modification Request:**
{data["prompt"]}

**Home Assistant Context:**
```json
{json.dumps(ha_context, indent=2)}
```
"""

        print(f"[DEBUG] Full prompt sent to LLM for editing:\n---\n{edit_prompt}\n---")

        llm_response = llm_provider.generate(edit_prompt, options)
        llm_response["context_summary"] = context_summary
        llm_response["prompt"] = data["prompt"]
        return jsonify(llm_response)
    except Exception as e:
        print(f"[ERROR] Error in edit_automation: {str(e)}")
        return jsonify({"error": str(e)}), 500


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
        print(f"[ERROR] Error in install_automation: {str(e)}")
        return jsonify({"error": str(e)}), 500
