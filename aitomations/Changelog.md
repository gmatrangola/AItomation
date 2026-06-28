# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-10-26

### Added
- Initial public release
- Support for Google Gemini and Ollama LLM providers
- Conversational UI with chat history
- Streaming responses with progress indicators
- Context-aware automation generation
- Installation directly from UI

## [1.0.1] - 2025-11-16

### Added
- User editibale system prompt with template replacement
- Better default system prompt
- Added rows to user propmt area
- Config is now a Vue page for better UX

## [1.1.0] - 2026-06-25

### Added
- Dashboard generation with one-click apply (Lovelace WebSocket API)
- Multiple applyable artifacts per response, each with its own apply button,
  applied in dependency order
- Apply support for scripts, scenes, and helper entities (input_boolean,
  input_number, input_select, input_text, input_datetime, input_button,
  timer, counter) in addition to automations
- Build stamp on the Configuration page (version, git commit, and build time)
  so you can tell which build is running

## [1.1.3] - 2026-06-28

### Fixed
- Applying an artifact whose generated YAML is malformed now shows a clear
  "couldn't be parsed" message with the offending line, instead of a generic
  "unexpected error"
- Copy buttons (per-code-block and "Copy Markdown") now work in the Home Assistant
  companion apps' webview, which lacks the secure-context clipboard API; the copy
  button also shows a "Copy failed" state if the platform blocks clipboard access

## [1.1.2] - 2026-06-28

### Added
- Copy-to-clipboard button on every code block, plus a "Copy Markdown" button at
  the top of each response to copy the whole reply as Markdown
- Per-artifact "Done" indicator after a component is applied, and an "Apply All"
  button that applies every artifact in dependency order (stops on first failure)
- Empty-state hint and examples now mention scripts, scenes, helpers, and dashboards
- "Done" button to finish a conversation — clears the prompt, responses, and history
  so you can start fresh
- "Helpers" button in the action bar opens a drawer listing existing helper entities
  (input_*/timer/counter), mirroring the Dashboards and Automations drawers

### Fixed
- Action bar (Done / Dashboards / Automations) was rendered behind the fixed top app
  bar and invisible; moved it below the prompt and fixed the app-bar offset
- Helpers (input_*/timer/counter) now apply correctly via the WebSocket
  storage-collection API; they were POSTing to a REST config endpoint that does
  not exist for helpers and failed with "404 Not Found"
- Each artifact's apply button now appears inline directly under its YAML block,
  instead of all buttons being grouped at the end of the response
