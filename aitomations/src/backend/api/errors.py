"""Structured error types for API responses."""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Standardized error codes for frontend localization."""

    # Connection errors
    HOSTNAME_RESOLUTION_FAILED = "HOSTNAME_RESOLUTION_FAILED"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    CONNECTION_LOST = "CONNECTION_LOST"
    NETWORK_ERROR = "NETWORK_ERROR"

    # Timeout errors
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"

    # Configuration errors
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    INVALID_API_KEY = "INVALID_API_KEY"
    INVALID_CONFIG = "INVALID_CONFIG"

    # HTTP errors
    HTTP_ERROR = "HTTP_ERROR"

    # LLM errors
    LLM_ERROR = "LLM_ERROR"

    # Dashboard / Lovelace errors
    DASHBOARD_ERROR = "DASHBOARD_ERROR"
    DASHBOARD_READONLY = "DASHBOARD_READONLY"

    # Helper (input_*/timer/counter) errors
    HELPER_ERROR = "HELPER_ERROR"

    # Input validation
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_YAML = "INVALID_YAML"
    UNSUPPORTED_KIND = "UNSUPPORTED_KIND"

    # Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class APIError(Exception):
    """Structured error for API responses."""

    def __init__(self, code: ErrorCode, context: dict[str, Any] | None = None):
        """
        Create a structured API error.

        Args:
            code: Error code for frontend localization
            context: Additional context for error message formatting
        """
        self.code = code
        self.context = context or {}
        super().__init__(code.value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {"error_code": self.code.value, "context": self.context}
