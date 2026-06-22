"""Minimal synchronous Home Assistant WebSocket client for Lovelace dashboards.

Lovelace/dashboard configuration is *not* exposed over the HA REST API; the only
programmatic read/write path is the WebSocket API. This module implements just enough
of that protocol to list dashboards and read/create/save their configuration.

It is intentionally synchronous (one short-lived connection per logical operation),
which is fine under gunicorn's threaded ``gthread`` workers.
"""

from __future__ import annotations

import json
from types import TracebackType
from typing import Any

from flask import current_app
from websocket import WebSocket, create_connection

from api.config import HA_WS_URL, SUPERVISOR_TOKEN
from api.errors import APIError, ErrorCode

# Connection/handshake timeout in seconds.
_WS_TIMEOUT = 15


class LovelaceClient:
    """Short-lived authenticated connection to HA's WebSocket API.

    Usage::

        with LovelaceClient() as client:
            dashboards = client.list_dashboards()
    """

    def __init__(self) -> None:
        self._ws: WebSocket | None = None
        self._msg_id = 0

    # --- context manager ---
    def __enter__(self) -> LovelaceClient:
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
            raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": "Supervisor token not available"})

        try:
            ws = create_connection(HA_WS_URL, timeout=_WS_TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.error("❌ Failed to open HA WebSocket: %s", exc)
            raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": f"WebSocket connection failed: {exc}"}) from exc

        # Auth handshake: auth_required -> auth -> auth_ok
        try:
            greeting = json.loads(ws.recv())
            if greeting.get("type") != "auth_required":
                raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": f"Unexpected greeting: {greeting.get('type')}"})

            ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
            auth_result = json.loads(ws.recv())
            if auth_result.get("type") != "auth_ok":
                ws.close()
                raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": "WebSocket authentication failed"})
        except APIError:
            raise
        except Exception as exc:  # noqa: BLE001
            ws.close()
            raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": f"WebSocket handshake error: {exc}"}) from exc

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
            raise APIError(ErrorCode.DASHBOARD_ERROR, {"details": "WebSocket not connected"})

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
                code = ErrorCode.DASHBOARD_ERROR
                # Storage-only dashboards in YAML mode cannot be written.
                if "yaml" in message.lower() or error.get("code") == "config_not_storage":
                    code = ErrorCode.DASHBOARD_READONLY
                raise APIError(code, {"details": message})
            return response.get("result")

    # --- public operations ---
    def list_dashboards(self) -> list[dict[str, Any]]:
        result = self._command({"type": "lovelace/dashboards/list"})
        return result if isinstance(result, list) else []

    def get_dashboard_config(self, url_path: str | None) -> Any:
        return self._command({"type": "lovelace/config", "url_path": url_path, "force": False})

    def save_dashboard_config(self, url_path: str | None, config: dict[str, Any]) -> None:
        self._command({"type": "lovelace/config/save", "url_path": url_path, "config": config})

    def create_dashboard(
        self,
        url_path: str,
        title: str,
        *,
        icon: str | None = None,
        show_in_sidebar: bool = True,
        require_admin: bool = False,
    ) -> dict[str, Any]:
        command: dict[str, Any] = {
            "type": "lovelace/dashboards/create",
            "url_path": url_path,
            "title": title,
            "show_in_sidebar": show_in_sidebar,
            "require_admin": require_admin,
        }
        if icon:
            command["icon"] = icon
        result = self._command(command)
        return result if isinstance(result, dict) else {}


def list_dashboards() -> list[dict[str, Any]]:
    """Convenience wrapper: list dashboards using a short-lived connection."""
    with LovelaceClient() as client:
        return client.list_dashboards()
