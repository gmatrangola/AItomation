from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, options: dict) -> dict:
        """
        Generates a response from the LLM.

        Args:
            prompt: The complete prompt to send to the LLM.
            options: A dictionary of configuration options.

        Returns:
            A dictionary parsed from the LLM's JSON response.
        """
        pass
