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
