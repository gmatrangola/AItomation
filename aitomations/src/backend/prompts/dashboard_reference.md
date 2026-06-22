# Home Assistant Reference (bundled baseline)

This is a compact reference for generating Home Assistant **dashboard (Lovelace)** and
**automation** YAML. It reflects HA `2024.12` and is used as a fallback when newer docs
cannot be fetched.

## Dashboards (Lovelace)

A dashboard config is a mapping with a top-level `views:` list. Each view holds `cards:`.

```yaml
# aitomation_kind: dashboard
title: My Dashboard
views:
  - title: Home
    path: home
    icon: mdi:home
    cards:
      - type: entities
        title: Living Room
        entities:
          - light.living_room
          - switch.living_room_fan
```

### Common card types

- `entities` — list of entities. Key: `entities` (list of ids or `{entity, name}`), `title`.
- `entity` — a single entity. Keys: `entity`, `name`, `icon`.
- `button` — actionable button. Keys: `entity`, `name`, `icon`, `tap_action`.
- `light` — light control with brightness. Key: `entity`.
- `thermostat` — climate control. Key: `entity`.
- `glance` — compact entity grid. Key: `entities`.
- `history-graph` / `statistics-graph` — trends. Key: `entities`.
- `gauge` — single numeric value. Keys: `entity`, `min`, `max`, `severity`.
- `markdown` — rich text. Key: `content`.
- `picture-glance` / `picture-entity` — image + entities. Keys: `image`, `entities`.
- `weather-forecast` — weather. Key: `entity` (a `weather.*` entity).
- `media-control` — media player. Key: `entity`.
- `map` — device trackers / zones. Key: `entities`.

### Layout cards

- `vertical-stack` / `horizontal-stack` — group cards. Key: `cards` (list).
- `grid` — grid layout. Keys: `cards`, `columns`, `square`.
- `conditional` — show a card based on state. Keys: `conditions`, `card`.
- `area` — all entities in an area. Key: `area`.

### Notes

- Reference only entities/areas that exist in the provided Home Assistant context.
- For a full-dashboard replacement provide the entire `views:` tree; for a modification of
  an existing dashboard, return the **complete updated config**, not just the delta.

## Automations

```yaml
# aitomation_kind: automation
alias: Porch light at sunset
description: Turn on the porch light at sunset
trigger:
  - platform: sun
    event: sunset
condition: []
action:
  - service: light.turn_on
    target:
      entity_id: light.porch
mode: single
```

- Triggers: `state`, `time`, `sun`, `numeric_state`, `template`, `zone`, `device`, `mqtt`.
- Conditions: `state`, `numeric_state`, `time`, `sun`, `template`, `and`/`or`/`not`.
- Actions: `service` calls (with `target`/`data`), `delay`, `wait_template`, `choose`, `if`.
- `mode`: `single`, `restart`, `queued`, `parallel`.
