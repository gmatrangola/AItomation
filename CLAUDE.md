# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AItomations is a **Home Assistant add-on** that turns natural-language requests into Home Assistant automation YAML using an LLM (Google Gemini or local Ollama). It ships as a single Docker container where a Python Flask backend serves both a REST/SSE API and the pre-built Vue 3 SPA as static files.

This repo is the *source*; end users install from a separate `aitomation-install` repo. The `image` field in `aitomations/config.json` is expected to be **absent on development branches** and present only on release tags (CI warns otherwise).

## Commands

Everything goes through the `Makefile` (run `make help` for the full list). Common ones:

```bash
make validate          # ruff + mypy (backend) + eslint/vue-tsc/prettier (frontend), cached
make validate-force    # same, ignoring the .make-cache/ cache
make lint-fix          # ruff --fix + ruff format + eslint --fix
make build             # clean + validate + build frontend + rsync into build/
make build-incremental # faster build, skips type-check (validate-quick)
make deploy TARGET=test    # build, then rsync over SSH to a HA instance (.deploy.<TARGET>.env)
make logs TARGET=test      # tail add-on container logs on the target
make release VERSION=x.y.z # tag + release via scripts/release.sh
```

Run servers locally (two terminals; the Vite dev server proxies `/api/*` to port 8099):

```bash
make dev-backend       # python3 app.py  -> http://localhost:8099
make dev-frontend      # pnpm run dev    -> http://localhost:5173
```

Validation caching: `make validate` touches marker files in `.make-cache/`. If validation seems to pass without re-running, use `make validate-force` or `make clean-cache`.

### Tests

There is **no real test suite yet** — no backend `test_*.py` files exist, and the frontend `package.json` has no `test` script. `make test` deliberately swallows failures (`|| true`). Don't assume `make test` proves anything; CI (`.github/workflows/ci.yml`) only runs `make validate`. If you add tests, backend uses pytest from `aitomations/src/backend/` (`make test-backend`).

## Directory layout gotchas

- **`build/` is generated** — it's an rsync mirror of `aitomations/` produced by `make build` and is git-ignored. Never edit anything under `build/`; edit the originals under `aitomations/` and rebuild.
- **`.tox/` dirs** under `aitomations/` and `build/` are virtualenvs — ignore them in searches.
- The real LLM provider code lives at **`aitomations/src/backend/llm/`** (not `src/llm/` as some older docs say).

## Backend architecture (`aitomations/src/backend/`)

- `app.py` — Flask entry point. Serves the SPA from `dist/` (catch-all route → `index.html`) and registers `api/routes.py` under `/api`. In production, `run.sh` launches it via **gunicorn with `gthread` workers** (threaded, required for SSE streaming) as `src.backend.app:app`; locally `app.py` runs Flask's dev server on `0.0.0.0:8099`.
- `api/routes.py` — all `/api/*` endpoints. The core one is `POST /generate_automation/stream`, a **Server-Sent Events** generator that emits `progress` / `content` / `done` / `error` events as the LLM streams.
- `api/config.py` — constants. Talks to Home Assistant via the **Supervisor proxy** at `http://supervisor/core/api`, authenticated with `SUPERVISOR_TOKEN` from the container env. Persistent files live at `/data/` (only exists inside the HA container): `options.json` (Supervisor-managed), `aitomations_config.json` (our state), `chat_history.json`.
- **Config layering**: `get_options()` reads Supervisor's read-only `/data/options.json`; `load_addon_state()` reads our writable `/data/aitomations_config.json`; `get_effective_config()` returns `{**options, **state}` (state wins). Secret fields (keys containing `"key"`) are masked as `"***"` in GET responses and preserved on save when the client sends back `"***"`.
- `api/context.py` — `get_ha_context()` fetches and compacts entities/services/areas/automations from HA into a dict for the prompt. Failures degrade gracefully (empty lists) rather than aborting.
- `api/prompting.py` — renders the system prompt with **Jinja2**. Uses the `system_prompt_template` option if set, else `prompts/default_system_prompt.jinja2`. Template vars: `ha_context`, `user_request`, `chat_history`.
- `api/errors.py` — `APIError` + `ErrorCode` enum. Error codes are strings shared with the frontend for localized messages; emit these (not raw strings) for user-facing failures.
- `llm/base.py` — `LLMProvider` ABC. `generate()` is abstract; `generate_stream()` defaults to chunking a full response. New providers subclass this and are wired in via `get_llm_provider()` in `routes.py`. Implementations: `llm/gemini.py`, `llm/ollama.py`.

## Frontend architecture (`aitomations/src/frontend/`)

Vue 3 + TypeScript + Vuetify, Composition API (`<script setup>`), built with Vite, package manager is **pnpm**.

- `services/chatService.ts` — consumes the SSE stream from `/generate_automation/stream` and extracts YAML from the assistant reply.
- `services/chatStorage.ts` / `configService.ts` / `errorService.ts` — persistence and config API wrappers; `errorService` maps backend `ErrorCode`s to messages.
- `composables/` — shared logic (`useChat.ts`, `useMarkdown.ts`).
- `types/` — `chat.ts`, `errors.ts` mirror backend shapes.

## Conventions

- Backend: ruff (line length 120, rules E/W/F/I/B/C4/UP/N) + mypy (`py311`); `from __future__ import annotations` is used throughout. Run `make lint-fix` before committing.
- Keep `version` in sync across `aitomations/config.json`, `aitomations/src/frontend/package.json`, and the README badge — CI warns on mismatch and `make check-version` shows all three.
- New user-facing config options must be added to `aitomations/config.json`'s `options`/`schema` so Supervisor surfaces them.

## Token Usage

Try to be efficient with Token usages when connecting to Fronter LLMs like Claude. For simple commands that might generate a lot of low-value tokens returned like git rebase etc., reply with commands that the user can run and wait for a response. 