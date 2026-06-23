# AItomations v2 — Development Plan

Working branch: `FixChatHistory`.

## Goal

Let the LLM emit **multiple applyable artifacts per response** (e.g. a helper + the script
that reads it + the dashboard that calls it), each with its own one-click apply button, and
give the backend real apply paths for every artifact kind that Home Assistant exposes through
a config API.

## Artifact contract

Every applyable YAML block in an assistant reply begins with marker comments the frontend
uses to route it (defined in `prompts/default_system_prompt.jinja2`, parsed in
`services/chatService.ts → extractArtifactsFromMarkdown`):

```yaml
# aitomation_kind: <kind>          # line 1, required
# aitomation_id: <snake_case_slug> # line 2 — required for script/scene/helpers, optional for automation, omitted for dashboard
# aitomation_url_path: <slug>      # line 3 — dashboards only
```

- `kind` is the **HA domain** (`automation`, `script`, `scene`, `input_boolean`, `input_number`,
  `input_select`, `input_text`, `input_datetime`, `input_button`, `timer`, `counter`), except
  `dashboard`, which is applied over the WebSocket Lovelace API.
- Blocks without a recognized `# aitomation_kind:` marker are illustrative only (no apply button).
- Multi-block responses must be ordered by dependency (helpers/scripts before the dashboards
  that reference them) — buttons apply in the order shown.

`ArtifactKind` is a single source of truth in `types/chat.ts` (`ARTIFACT_KINDS` derives the
type; `HELPER_KINDS` flags the helper subset for generic rendering).

## Apply routing

| Kind | Endpoint | Mechanism |
|---|---|---|
| automation | `POST /api/install_automation` | `_apply_config_entity("automation", …)` → HA `config/automation/config/<id>` |
| script, scene, helpers | `POST /api/apply_entity` | `_apply_config_entity(kind, …)` → HA `config/<kind>/config/<id>` |
| dashboard | `POST /api/apply_dashboard` | `LovelaceClient` WebSocket save/create |

`_apply_config_entity(kind, entity_id, config_yaml, prompt)` (in `api/routes.py`) is the shared
core: parses YAML, resolves the object id (explicit `aitomation_id` → config `id` → slug of
`name`/`alias`), attaches provenance metadata for automations only (helpers/scenes validate
against stricter schemas), and POSTs to the kind's HA config endpoint. `APPLY_KINDS` is the
allow-list; unknown kinds raise `UNSUPPORTED_KIND` (HTTP 400).

---

## Status

### Phase 1 — Multi-artifact output contract ✅ COMPLETE
- System prompt emits multiple marked YAML blocks per reply.
- Frontend: `Artifact[]` model, `extractArtifactsFromMarkdown`, per-artifact apply buttons in
  `ChatMessage.vue`, single `apply-artifact` emit, buttons shown only on the most recent
  artifact message. Legacy `yaml`/`artifactKind` history shapes still render.

### Phase 2 — Script & scene apply ✅ COMPLETE
- Backend: generic `_apply_config_entity` + `POST /apply_entity`; `install_automation`
  refactored to a thin wrapper. Added `UNSUPPORTED_KIND` error code.
- Frontend: `services/entityService.ts`, `handleApplyEntity` in `Dashboard.vue`, dynamic
  success snackbar, `UNSUPPORTED_KIND` message in `errorService.ts`.

### Phase 3 — Helper kinds ✅ COMPLETE
- Backend: `input_boolean`, `input_number`, `input_select`, `input_text`, `input_datetime`,
  `input_button`, `timer`, `counter` added to `APPLY_KINDS` (the generic helper handles them).
- Frontend: helper kinds render generically (label `Create <Pretty Name>`, icon
  `mdi-tune-variant`, color `info`); `Dashboard.vue` `default` branch routes them to
  `/apply_entity`; snackbar prettifies `input_boolean` → "Input Boolean".
- System prompt: helper domains added to the contract + a "Helper block" section with examples.

### Phase 4 — Light/entity groups ⏸ DEFERRED
Groups have **no clean config REST API** — they require driving HA's Groups integration
**config flow over WebSocket** (multi-step, version-sensitive). `api/lovelace.py`'s
`LovelaceClient` is the model for a future synchronous WS config-flow client. The system prompt
already steers toward the helper-first pattern (`light.all`, area cards, light groups) so this
is low-urgency.

### Optional / not yet built
- **"Apply All"** button when a message has multiple artifacts (apply in dependency order with
  per-artifact status).
- **Cleanup:** vestigial `latestYaml` ref in `useChat.ts` (superseded by `lastArtifactMessageId`).

---

## Validation (every change must pass)

```bash
make validate          # ruff + mypy (backend) + eslint/vue-tsc/prettier (frontend), cached
make validate-force    # ignore the .make-cache/ cache
make lint-fix          # ruff --fix + ruff format + eslint --fix (run before committing)
```

There is no automated test suite yet (`make test` swallows failures); CI only runs
`make validate`. The features below must be verified manually on a live HA instance.

---

## Local development

Two terminals; the Vite dev server proxies `/api/*` to the backend on `:8099`.

```bash
make dev-backend       # python3 app.py -> http://localhost:8099
make dev-frontend      # pnpm run dev   -> http://localhost:5173
```

`make dev-backend` auto-creates `./.dev-data/` (gitignored) and points `AITOMATIONS_DATA_DIR`
at it, so the backend runs outside the HA container. Note: without `SUPERVISOR_TOKEN` and the
Supervisor proxy, calls that reach Home Assistant (context fetch, automation/helper/dashboard
apply) will fail — local dev is for UI and stream wiring; **apply paths must be tested on a
real HA instance.**

---

## Deploy to a Home Assistant instance

Deployment rsyncs the built add-on over SSH into the HA `addons/` share, then HA's Supervisor
rebuilds the add-on container.

### One-time setup
Connection settings come from `.deploy.env` (defaults: `HA_USER`, `HA_PORT`, `HA_PATH`) overlaid
by a per-target `.deploy.<TARGET>.env` (both gitignored). Create your target env with at least
`HA_HOST` (and override others as needed):

```bash
# .deploy.test.env
HA_HOST=homeassistant.local
HA_USER=root
HA_PORT=22
HA_PATH=/addons/aitomations-creator
```

SSH access to the HA host is required (e.g. the "Advanced SSH & Web Terminal" add-on).

### Deploy + restart + watch logs

```bash
make deploy TARGET=test    # clean + validate + build frontend + rsync to the HA share
make restart TARGET=test   # remove the add-on container so Supervisor rebuilds it
make logs TARGET=test      # tail add-on container logs (follow)
make status TARGET=test    # show the add-on container status
```

`TARGET` defaults to `test`. After `make deploy`, in the HA UI: **Settings → Add-ons →** reload /
check for updates, **restart the AItomations add-on**, then hard-refresh the browser
(Ctrl/Cmd+Shift+R) to bust the cached SPA.

> Note: keep the `image` field **absent** from `aitomations/config.json` on development
> branches — local deploys build from source. It is set only on release tags.

---

## Manual E2E test checklist (v2 features)

Run after `make deploy TARGET=test` against a real HA instance. Tail `make logs TARGET=test`
in parallel and watch for `✅ Applied <kind> (id=…)` / error lines.

**Single-artifact apply (per kind)** — prompt the chat, confirm one apply button with the
right label/color, click it, confirm the success snackbar, then verify the entity exists in HA:

- [ ] Automation → *"Turn on the porch light at sunset."* → appears under Settings → Automations.
- [ ] Script → *"Make a script that turns off all the lights."* → appears under Settings → Scripts.
- [ ] Scene → *"Create a movie-night scene that dims the living room."* → Settings → Scenes.
- [ ] `input_boolean` → *"Add a Vacation Mode toggle."* → Settings → Devices & Services → Helpers.
- [ ] `input_number` → *"Add a target temperature helper from 15 to 28."* → Helpers.
- [ ] Spot-check one more helper (`input_select` / `timer` / `counter`).

**Multi-artifact apply (dependency order)**
- [ ] *"Make a button on a new dashboard that turns off all lights."* → response has a **script**
      block then a **dashboard** block, each with its own button. Apply script first, then
      dashboard. Open the dashboard link from the snackbar; confirm the button calls the script.
- [ ] *"Add a Vacation Mode toggle and an automation that arms the alarm when it's on."* →
      helper block + automation block; apply both; toggle the helper and confirm the automation fires.

**Regression / edge cases**
- [ ] Buttons appear only on the **most recent** artifact message.
- [ ] An illustrative ```yaml block without a marker shows **no** apply button.
- [ ] Old `chat_history.json` (legacy `yaml`/`artifactKind`) still renders an apply button.
- [ ] Apply failure (e.g. invalid YAML / unknown kind) surfaces a readable error banner, not a crash.
- [ ] Gemini provider: a prompt naming `lock`/`alarm_control_panel`/`garage_door` is **not**
      blocked by the safety filter (returns a clean result or a clean `APIError`).
