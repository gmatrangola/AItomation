"""Synchronous Home Assistant WebSocket client base + storage-collection helpers.

Some things HA can do are *not* exposed over the REST API and are only reachable over the
WebSocket API:

- Lovelace dashboards (see ``LovelaceClient`` in ``lovelace.py``).
- The ``input_*`` / ``timer`` / ``counter`` "helpers", which are **storage-collection**
  entities. The REST ``config/<domain>/config/<id>`` endpoints only exist for
  automation/script/scene; helpers must be created via ``<domain>/create`` over WebSocket.

This module holds the shared connection/auth/command plumbing (``HAWebSocketClient``) plus
``HelperClient`` for creating helpers. It is intentionally synchronous (one short-lived
connection per logical operation), which is fine under gunicorn's threaded ``gthread`` workers.
"""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any, Self

from flask import current_app
from websocket import WebSocket, create_connection

from api.config import HA_WS_URL, SUPERVISOR_TOKEN
from api.errors import APIError, ErrorCode

# Connection/handshake timeout in seconds.
_WS_TIMEOUT = 15


class HAWebSocketClient:
    """Short-lived authenticated connection to HA's WebSocket API.

    Subclasses set ``_ws_error`` to the error code their operations should raise and add
    domain-specific command methods built on ``_command``.
    """

    # Error code raised for connection/command failures (overridden by subclasses).
    _ws_error: ErrorCode = ErrorCode.UNKNOWN_ERROR

    def __init__(self) -> None:
        self._ws: WebSocket | None = None
        self._msg_id = 0

    # --- context manager ---
    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- connection lifecycle ---
    def connect(self) -> None:
        if not SUPERVISOR_TOKEN:
            raise APIError(self._ws_error, {"details": "Supervisor token not available"})

        try:
            ws = create_connection(HA_WS_URL, timeout=_WS_TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.error("❌ Failed to open HA WebSocket: %s", exc)
            raise APIError(self._ws_error, {"details": f"WebSocket connection failed: {exc}"}) from exc

        # Auth handshake: auth_required -> auth -> auth_ok
        try:
            greeting = json.loads(ws.recv())
            if greeting.get("type") != "auth_required":
                raise APIError(self._ws_error, {"details": f"Unexpected greeting: {greeting.get('type')}"})

            ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
            auth_result = json.loads(ws.recv())
            if auth_result.get("type") != "auth_ok":
                ws.close()
                raise APIError(self._ws_error, {"details": "WebSocket authentication failed"})
        except APIError:
            raise
        except Exception as exc:  # noqa: BLE001
            ws.close()
            raise APIError(self._ws_error, {"details": f"WebSocket handshake error: {exc}"}) from exc

        self._ws = ws

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    # --- command plumbing ---
    def _command(self, command: dict[str, Any]) -> Any:
        """Send one command and return its ``result`` payload, raising on failure."""
        if self._ws is None:
            raise APIError(self._ws_error, {"details": "WebSocket not connected"})

        self._msg_id += 1
        msg_id = self._msg_id
        self._ws.send(json.dumps({"id": msg_id, **command}))

        # Skip any unrelated event frames until we get the matching result.
        while True:
            response = json.loads(self._ws.recv())
            if response.get("id") != msg_id:
                continue
            if response.get("type") != "result":
                continue
            if not response.get("success", False):
                error = response.get("error", {}) or {}
                message = error.get("message", "Unknown WebSocket error")
                code = self._ws_error
                # Storage-only dashboards in YAML mode cannot be written.
                if self._ws_error == ErrorCode.DASHBOARD_ERROR and (
                    "yaml" in message.lower() or error.get("code") == "config_not_storage"
                ):
                    code = ErrorCode.DASHBOARD_READONLY
                raise APIError(code, {"details": message})
            return response.get("result")


# Keys that can appear in generated helper YAML but aren't valid create fields.
_HELPER_STRIP_KEYS = {"platform", "id", "entity_id"}


class HelperClient(HAWebSocketClient):
    """Create ``input_*`` / ``timer`` / ``counter`` helpers via storage-collection commands."""

    _ws_error = ErrorCode.HELPER_ERROR

    def create_helper(self, domain: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a helper of ``domain`` (e.g. ``input_datetime``) from ``fields``.

        HA assigns the entity_id from the helper's name; the generated ``# aitomation_id``
        marker can't be enforced here (storage collections don't accept an explicit id).
        """
        payload = {k: v for k, v in fields.items() if k not in _HELPER_STRIP_KEYS}
        result = self._command({"type": f"{domain}/create", **payload})
        return result if isinstance(result, dict) else {}
