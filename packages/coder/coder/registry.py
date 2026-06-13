"""Provider registry mapping model names to LLM providers.

Maps model name prefixes to provider constructors using a deterministic
resolution strategy: ``claude-`` -> Anthropic, ``gemini-`` -> Google,
all others -> Ollama. Custom prefix-to-provider mappings can be registered
to override defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from coder.providers import (
    AnthropicProvider,
    GoogleProvider,
    LLMProvider,
    OllamaProvider,
)


@dataclass(frozen=True)
class ModelInfo:
    """Describes a model name pattern and its associated provider.

    Attributes:
        name: The model name prefix or pattern.
        provider: The provider type name (e.g., ``anthropic``).
        description: A human-readable description of the mapping.
    """

    name: str
    provider: str
    description: str


# Type alias for provider constructors: callable that takes a model
# name string and returns an LLMProvider instance.
ProviderConstructor = Callable[[str], LLMProvider]


class ProviderRegistry:
    """Maps model name patterns to provider constructors.

    Supports prefix-based resolution with a deterministic fallback to
    Ollama for any unrecognized model name. Custom prefix-to-provider
    mappings can be registered and take precedence over built-in ones.
    """

    def __init__(self) -> None:
        # Ordered list of (prefix, constructor) pairs. Custom entries
        # are prepended to take priority over built-in mappings.
        self._prefix_map: list[tuple[str, ProviderConstructor]] = [
            ("claude-", AnthropicProvider),
            ("gemini-", GoogleProvider),
        ]

    def resolve(self, model_name: str) -> LLMProvider:
        """Create a provider for the given model name.

        Resolution uses prefix matching against registered patterns.
        If no prefix matches, falls back to OllamaProvider.

        Args:
            model_name: The model name to resolve.

        Returns:
            A configured LLMProvider instance.

        Raises:
            ValueError: If model_name is empty.
        """
        if not model_name:
            raise ValueError(
                "Model name must not be empty. Provide a model name "
                "like 'claude-opus-4-6', 'gemini-2.5-pro', or an "
                "Ollama model tag."
            )

        for prefix, constructor in self._prefix_map:
            if model_name.startswith(prefix):
                return constructor(model_name)

        # Fallback: treat as Ollama model tag
        return OllamaProvider(model_name)

    def register(
        self, prefix: str, constructor: ProviderConstructor
    ) -> None:
        """Register a custom prefix-to-provider mapping.

        Custom registrations are prepended to the resolution list,
        giving them priority over built-in mappings.

        Args:
            prefix: The model name prefix to match.
            constructor: A callable that takes a model name string
                and returns an LLMProvider instance.
        """
        # Prepend so custom mappings have highest priority
        self._prefix_map.insert(0, (prefix, constructor))

    def list_models(self) -> list[ModelInfo]:
        """Return all known model patterns.

        Returns a list of ModelInfo entries describing each registered
        prefix and the Ollama fallback.

        Returns:
            A list of ModelInfo instances.
        """
        models: list[ModelInfo] = []

        for prefix, constructor in self._prefix_map:
            provider_name = constructor.__name__.replace(
                "Provider", ""
            ).lower()
            # Determine a human-readable description
            if constructor is AnthropicProvider:
                desc = (
                    "Anthropic Claude models (e.g., claude-opus-4-6)"
                )
            elif constructor is GoogleProvider:
                desc = (
                    "Google Gemini models (e.g., gemini-2.5-pro)"
                )
            else:
                desc = f"Custom provider for '{prefix}' prefix"

            models.append(
                ModelInfo(
                    name=f"{prefix}*",
                    provider=provider_name,
                    description=desc,
                )
            )

        # Always include the Ollama fallback
        models.append(
            ModelInfo(
                name="<other>",
                provider="ollama",
                description=(
                    "Ollama local models (fallback for unrecognized "
                    "names)"
                ),
            )
        )

        return models
