from __future__ import annotations

from typing import Any

import requests
from flask import current_app

from api.config import HA_API_URL, HA_HEADERS  # reuse existing constants


def _ha_get(path: str) -> Any:
    url = f"{HA_API_URL}{path}"
    resp = requests.get(url, headers=HA_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_ha_context() -> tuple[dict, str]:
    """
    Build a compact but rich Home Assistant context for the LLM.

    Returns:
        (ha_context, summary_string)
    """
    current_app.logger.info("🌐 Fetching Home Assistant context")

    context: dict[str, Any] = {}

    # --- Config (timezone, units) ---
    try:
        config = _ha_get("/config")
        context["config"] = {
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system", {}).get("name"),
        }
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(f"⚠️ Failed to fetch /config: {exc}")
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

        for state in states:
            entity_id = state.get("entity_id")
            attrs = state.get("attributes", {})
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

    except Exception:  # noqa: BLE001
        current_app.logger.error("❌ Failed to fetch /states", exc_info=True)
        context.setdefault("entities", [])
        context.setdefault("helpers", {})
        context.setdefault("scenes", [])

    # --- Areas (via entity attributes only, summarized) ---
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
                    "name": area_id,  # HA may have a nicer name in registries; fallback to id
                    "entities_by_domain": {},
                },
            )
            domain = ent.get("domain", "unknown")
            area["entities_by_domain"].setdefault(domain, []).append(ent["id"])

        context["areas"] = list(areas_by_id.values())
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(f"⚠️ Failed to build areas summary: {exc}")
        context["areas"] = []

    # --- Services (flat list of domain.service strings) ---
    try:
        services_raw = _ha_get("/services")
        services: list[str] = []
        for svc_domain in services_raw:
            domain = svc_domain.get("domain")
            for svc in svc_domain.get("services", {}).keys():
                services.append(f"{domain}.{svc}")
        context["services"] = services
    except Exception:  # noqa: BLE001
        current_app.logger.error("❌ Failed to fetch /services", exc_info=True)
        context.setdefault("services", [])

    # --- Automations (compact, with optional summary) ---
    try:
        automations_raw = _ha_get("/states")
        autos: list[dict[str, Any]] = []
        for state in automations_raw:
            entity_id = state.get("entity_id")
            if not entity_id or not entity_id.startswith("automation."):
                continue
            attrs = state.get("attributes", {})
            alias = attrs.get("friendly_name", entity_id)
            summary = attrs.get("description") or attrs.get("summary")
            autos.append(
                {
                    "id": entity_id,
                    "name": alias,
                    "summary": summary,
                }
            )
        context["automations"] = autos
    except Exception:  # noqa: BLE001
        current_app.logger.error("❌ Failed to fetch automations summary", exc_info=True)
        context.setdefault("automations", [])

    summary = (
        f"entities={len(context.get('entities', []))}, "
        f"services={len(context.get('services', []))}, "
        f"automations={len(context.get('automations', []))}, "
        f"areas={len(context.get('areas', []))}"
    )
    current_app.logger.info(f"✅ HA context ready: {summary}")

    return context, summary
