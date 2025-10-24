from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, options: dict) -> dict:
        """
        Generates a response from the LLM (non-streaming).

        Args:
            prompt: The complete prompt to send to the LLM.
            options: A dictionary of configuration options.

        Returns:
            A dictionary with the complete response.
        """
        pass

    def generate_stream(self, prompt: str, options: dict) -> Iterator[str]:
        """
        Generates a streaming response from the LLM.

        Args:
            prompt: The complete prompt to send to the LLM.
            options: A dictionary of configuration options.

        Yields:
            Chunks of text as they become available.

        Default implementation: falls back to non-streaming.
        """
        # Default implementation for providers without native streaming
        result = self.generate(prompt, options)
        full_response = result.get("full_response", "")

        # Simulate streaming by chunking the response
        chunk_size = 50
        for i in range(0, len(full_response), chunk_size):
            yield full_response[i : i + chunk_size]
