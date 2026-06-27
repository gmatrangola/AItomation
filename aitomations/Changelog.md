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

## [1.1.1] - 2026-06-26

### Added
- Copy-to-clipboard button on every code block, plus a "Copy Markdown" button at
  the top of each response to copy the whole reply as Markdown
- Per-artifact "Done" indicator after a component is applied, and an "Apply All"
  button that applies every artifact in dependency order (stops on first failure)
- Empty-state hint and examples now mention scripts, scenes, helpers, and dashboards
- "Done" button to finish a conversation — clears the prompt, responses, and history
  so you can start fresh

### Fixed
- Helpers (input_*/timer/counter) now apply correctly via the WebSocket
  storage-collection API; they were POSTing to a REST config endpoint that does
  not exist for helpers and failed with "404 Not Found"
- Each artifact's apply button now appears inline directly under its YAML block,
  instead of all buttons being grouped at the end of the response
