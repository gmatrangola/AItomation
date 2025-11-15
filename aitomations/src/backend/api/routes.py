import json
import os
import re
import time
import traceback
from typing import Any  # <- only Any is needed now

import requests
import yaml
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from jinja2 import Environment, FileSystemLoader, Template, TemplateError

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

# Setup Jinja2 for prompt templates
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
jinja_env = Environment(loader=FileSystemLoader(PROMPTS_DIR), autoescape=False)


# --- Helper to log template directory (called lazily) ---
_prompts_dir_logged = False


def _log_prompts_dir() -> None:
    """Log prompts directory info - only called when needed."""
    global _prompts_dir_logged
    if not _prompts_dir_logged:
        current_app.logger.info(f"📂 PROMPTS_DIR resolved to: {PROMPTS_DIR}")
        current_app.logger.info(f"📂 Directory exists: {os.path.exists(PROMPTS_DIR)}")
        if os.path.exists(PROMPTS_DIR):
            current_app.logger.info(f"📂 Files in directory: {os.listdir(PROMPTS_DIR)}")
        else:
            current_app.logger.warning("⚠️  PROMPTS_DIR does not exist!")
            # Log the absolute path to help debug
            abs_path = os.path.abspath(PROMPTS_DIR)
            current_app.logger.warning(f"⚠️  Absolute path: {abs_path}")
            # List parent directory
            parent_dir = os.path.dirname(PROMPTS_DIR)
            if os.path.exists(parent_dir):
                current_app.logger.info(f"📂 Parent directory contents: {os.listdir(parent_dir)}")
        _prompts_dir_logged = True


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


def render_system_prompt(ha_context: dict, user_request: str, chat_history: list[dict] | None = None) -> str:
    """
    Render the system prompt using Jinja2 template.

    Args:
        ha_context: Home Assistant context (entities, services, automations, etc.)
        user_request: Current user request text
        chat_history: Recent messages (already truncated)

    Returns:
        Rendered prompt string
    """
    from flask import current_app

    global _prompts_dir_logged
    _log_prompts_dir()

    options = get_options()
    custom_template = (options.get("system_prompt_template") or "").strip()
    chat_history = chat_history or []

    try:
        if custom_template:
            current_app.logger.info("📝 Using custom system prompt template from options")
            template = Template(custom_template)
        else:
            current_app.logger.info("📝 Using default_system_prompt.jinja2")
            template = jinja_env.get_template("default_system_prompt.jinja2")

        rendered = template.render(
            ha_context=ha_context,
            user_request=user_request,
            chat_history=chat_history,
        )

        current_app.logger.debug("=== Rendered system prompt start ===")
        current_app.logger.debug(rendered)
        current_app.logger.debug("=== Rendered system prompt end ===")
        current_app.logger.info(f"📊 Prompt length: {len(rendered)} characters")

        return rendered
    except TemplateError as e:
        current_app.logger.error(f"❌ Template rendering error: {e}", exc_info=True)
        # Fallback: minimal but safe prompt
        return (
            "You are a Home Assistant automation assistant.\n\n"
            f"Context: {json.dumps(ha_context, indent=2)}\n\n"
            f"Chat History: {json.dumps(chat_history, indent=2)}\n\n"
            f"User Request: {user_request}\n\n"
            "Generate a YAML automation with an explanation."
        )


def _get_ha_context() -> tuple[dict, str]:
    """
    Build a compact but rich Home Assistant context for the LLM.

    Returns:
        (ha_context, summary_string)
    """
    current_app.logger.info("🌐 Fetching Home Assistant context")

    def _ha_get(path: str) -> Any:
        url = f"{HA_API_URL}{path}"
        resp = requests.get(url, headers=HA_HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()

    context: dict[str, Any] = {}

    # --- Config (timezone, units) ---
    try:
        config = _ha_get("/config")
        context["config"] = {
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system", {}).get("name"),
        }
    except Exception as e:
        current_app.logger.warning(f"⚠️ Failed to fetch /config: {e}")
        context["config"] = {}

    # --- Entities (compact) ---
    try:
        states = _ha_get("/states")
        entities: list[dict[str, Any]] = []
        helpers: dict[str, list[str]] = {
            "input_boolean": [],
            "input_datetime": [],
            "input_number": [],
            "other": [],
        }
        scenes: list[str] = []

        for s in states:
            entity_id = s.get("entity_id")
            attrs = s.get("attributes", {})
            name = attrs.get("friendly_name", entity_id)
            if not entity_id:
                continue

            domain = entity_id.split(".")[0]

            entities.append(
                {
                    "id": entity_id,
                    "name": name,
                    "domain": domain,
                    # area_id is helpful for grouping; may be None
                    "area_id": attrs.get("area_id"),
                }
            )

            # classify helpers & scenes
            if domain == "input_boolean":
                helpers["input_boolean"].append(entity_id)
            elif domain == "input_datetime":
                helpers["input_datetime"].append(entity_id)
            elif domain == "input_number":
                helpers["input_number"].append(entity_id)
            elif domain.startswith("input_"):
                helpers["other"].append(entity_id)
            elif domain == "scene":
                scenes.append(entity_id)

        context["entities"] = entities
        context["helpers"] = helpers
        context["scenes"] = scenes

    except Exception as e:
        current_app.logger.error(f"❌ Failed to fetch /states: {e}", exc_info=True)
        context.setdefault("entities", [])
        context.setdefault("helpers", {})
        context.setdefault("scenes", [])

    # --- Areas (via entity attributes only, summarized) ---
    # We don't use the registries here (keeps it simple and avoids WS).
    # Instead, infer areas from entity attributes if present.
    areas_by_id: dict[str, dict[str, Any]] = {}
    try:
        for ent in context.get("entities", []):
            area_id = ent.get("area_id")
            if not area_id:
                continue
            area = areas_by_id.setdefault(
                area_id,
                {
                    "id": area_id,
                    "name": area_id,  # HA often has a nicer name in registries; fallback to id
                    "entities_by_domain": {},
                },
            )
            domain = ent.get("domain", "unknown")
            area["entities_by_domain"].setdefault(domain, []).append(ent["id"])

        # Convert to list for the template
        context["areas"] = list(areas_by_id.values())
    except Exception as e:
        current_app.logger.warning(f"⚠️ Failed to build areas summary: {e}")
        context["areas"] = []

    # --- Services (flat list of domain.service strings) ---
    try:
        services_raw = _ha_get("/services")
        services: list[str] = []
        for svc_domain in services_raw:
            domain = svc_domain.get("domain")
            for s in svc_domain.get("services", {}).keys():
                services.append(f"{domain}.{s}")
        context["services"] = services
    except Exception as e:
        current_app.logger.error(f"❌ Failed to fetch /services: {e}", exc_info=True)
        context.setdefault("services", [])

    # --- Automations (compact, with optional summary) ---
    try:
        automations_raw = _ha_get("/states")
        # filter states for automation domain only
        autos: list[dict[str, Any]] = []
        for s in automations_raw:
            entity_id = s.get("entity_id")
            if not entity_id or not entity_id.startswith("automation."):
                continue
            attrs = s.get("attributes", {})
            alias = attrs.get("friendly_name", entity_id)
            # simple, compact summary if available
            summary = attrs.get("description") or attrs.get("summary")
            autos.append(
                {
                    "id": entity_id,
                    "name": alias,
                    "summary": summary,
                }
            )
        context["automations"] = autos
    except Exception as e:
        current_app.logger.error(f"❌ Failed to fetch automations summary: {e}", exc_info=True)
        context.setdefault("automations", [])

    # --- Build a small textual summary for logging / progress ---
    summary = (
        f"entities={len(context.get('entities', []))}, "
        f"services={len(context.get('services', []))}, "
        f"automations={len(context.get('automations', []))}, "
        f"areas={len(context.get('areas', []))}"
    )
    current_app.logger.info(f"✅ HA context ready: {summary}")

    return context, summary


# --- API Endpoints ---
@api_blueprint.route("/health")
def health_check():
    return jsonify({"status": "healthy"})


@api_blueprint.route("/config", methods=["POST"])
def save_config():
    """Save configuration to options.json"""
    try:
        data = request.get_json() or {}
        existing = get_options()

        # Preserve any masked secret fields containing 'key'
        for k, v in list(data.items()):
            if "key" in k.lower() and v == "***":
                # Keep existing real value if present
                if existing.get(k):
                    data[k] = existing[k]
                else:
                    # No existing value; treat as empty
                    data[k] = ""

        if data.get("llm_provider") not in ["gemini", "ollama"]:
            return jsonify({"error": "Invalid LLM provider"}), 400

        with open(OPTIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)

        current_app.logger.info("✅ Configuration saved successfully")
        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f"❌ Error saving configuration: {e}")
        return jsonify({"error": str(e)}), 500


@api_blueprint.route("/config")
def get_config():
    options = get_options()
    safe_config: dict[str, object] = {}
    for k, v in options.items():
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

            options = get_options()
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

            ha_context, context_summary = _get_ha_context()

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

            # --- NEW: pass trimmed history into prompt rendering ---
            current_app.logger.info("🔨 Rendering system prompt from template...")
            # pass both full_context (current user request) and trimmed_history
            creation_prompt = render_system_prompt(
                ha_context,
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

        # Fetch real Home Assistant context
        try:
            ha_context, _ = _get_ha_context()
        except Exception as e:
            return jsonify({"error": f"Failed to fetch Home Assistant data: {str(e)}"}), 500

        sample_request = "Turn on the living room lights when motion is detected after sunset"
        sample_history: list[dict[str, str]] = []  # or a small hard-coded sample if you prefer

        template = Template(template_str)
        rendered = template.render(
            ha_context=ha_context,
            user_request=sample_request,
            chat_history=sample_history,  # <-- add this
        )

        return jsonify({"rendered": rendered})
    except TemplateError as e:
        return jsonify({"error": f"Template error: {str(e)}"}), 400
    except Exception as e:
        current_app.logger.error(f"❌ Error previewing template: {e}")
        return jsonify({"error": str(e)}), 500
