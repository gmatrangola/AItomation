"""Minimal synchronous Home Assistant WebSocket client for Lovelace dashboards.

Lovelace/dashboard configuration is *not* exposed over the HA REST API; the only
programmatic read/write path is the WebSocket API. This module implements just enough
of that protocol to list dashboards and read/create/save their configuration.

The connection/auth/command plumbing lives in ``HAWebSocketClient`` (``ha_ws.py``), shared
with the helper-creation client.
"""

from __future__ import annotations

from typing import Any

from api.errors import ErrorCode
from api.ha_ws import HAWebSocketClient


class LovelaceClient(HAWebSocketClient):
    """Short-lived authenticated connection to HA's WebSocket API for dashboards.

    Usage::

        with LovelaceClient() as client:
            dashboards = client.list_dashboards()
    """

    _ws_error = ErrorCode.DASHBOARD_ERROR

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
