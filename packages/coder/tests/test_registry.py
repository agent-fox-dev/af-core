"""Tests for provider registry.

Test Spec Entries: TS-12-7, TS-12-8, TS-12-9, TS-12-22, TS-12-23,
TS-12-E2, TS-12-P1.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from coder.providers import (
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider,
)
from coder.registry import ProviderRegistry
from hypothesis import given, settings
from hypothesis import strategies as st


class TestProviderResolution:
    """Tests for model name to provider resolution."""

    def test_claude_prefix(self, fake_anthropic_key: str) -> None:
        """TS-12-7: Registry resolves claude- prefix to Anthropic.

        Requirement: 12-REQ-3.2
        Verifies registry maps claude- prefix to AnthropicProvider.
        """
        registry = ProviderRegistry()
        provider = registry.resolve("claude-opus-4-6")
        assert isinstance(provider, AnthropicProvider)

    def test_gemini_prefix(self, fake_google_key: str) -> None:
        """TS-12-8: Registry resolves gemini- prefix to Google.

        Requirement: 12-REQ-3.3
        Verifies registry maps gemini- prefix to GoogleProvider.
        """
        registry = ProviderRegistry()
        provider = registry.resolve("gemini-2.5-pro")
        assert isinstance(provider, GoogleProvider)

    def test_ollama_fallback(self) -> None:
        """TS-12-9: Registry falls back to Ollama for unknown prefix.

        Requirement: 12-REQ-3.4
        Verifies unknown model names are sent to Ollama.
        """
        registry = ProviderRegistry()
        provider = registry.resolve("codestral:latest")
        assert isinstance(provider, OllamaProvider)

    def test_registry_returns_provider(
        self, fake_anthropic_key: str
    ) -> None:
        """TS-12-22: ProviderRegistry returns configured LLMProvider.

        Requirement: 12-REQ-3.1
        Verifies ProviderRegistry maps model name patterns to provider
        constructors and returns a configured LLMProvider instance.
        """
        registry = ProviderRegistry()
        provider = registry.resolve("claude-opus-4-6")
        assert hasattr(provider, "model_name")
        assert hasattr(provider, "invoke")
        assert provider.model_name == "claude-opus-4-6"


class TestCustomRegistration:
    """Tests for custom provider registration."""

    def test_custom_registration(self) -> None:
        """TS-12-23: Registry allows custom model-to-provider mappings.

        Requirement: 12-REQ-3.5
        Verifies users can register custom prefix-to-provider mappings
        that override the default resolution.
        """
        mock_constructor = MagicMock()
        mock_provider = MagicMock()
        mock_provider.model_name = "custom-model"
        mock_constructor.return_value = mock_provider

        registry = ProviderRegistry()
        registry.register("custom-", mock_constructor)
        provider = registry.resolve("custom-model")
        assert provider is mock_provider
        mock_constructor.assert_called_once_with("custom-model")


class TestRegistryEdgeCases:
    """Edge case tests for provider registry."""

    def test_empty_model_name(self) -> None:
        """TS-12-E2: Empty model name rejected.

        Requirement: 12-REQ-3.E1
        Verifies registry rejects empty model name.
        """
        registry = ProviderRegistry()
        with pytest.raises(ValueError):
            registry.resolve("")


class TestRegistryProperties:
    """Property-based tests for provider resolution."""

    @settings(max_examples=50)
    @given(
        model_name=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                categories=("L", "N", "P", "S"),
                exclude_characters="\x00",
            ),
        ),
    )
    def test_property_provider_resolution(
        self, model_name: str
    ) -> None:
        """TS-12-P1: Provider resolution is deterministic.

        Property 1 from design.md.
        Validates: 12-REQ-3.2, 12-REQ-3.3, 12-REQ-3.4
        For any model name, the registry always resolves to the same
        provider type.
        """
        # Set fake keys for providers that need them
        old_anthropic = os.environ.get("ANTHROPIC_API_KEY")
        old_google = os.environ.get("GOOGLE_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        os.environ["GOOGLE_API_KEY"] = "test-key"

        try:
            registry = ProviderRegistry()
            provider = registry.resolve(model_name)

            if model_name.startswith("claude-"):
                assert isinstance(provider, AnthropicProvider)
            elif model_name.startswith("gemini-"):
                assert isinstance(provider, GoogleProvider)
            else:
                assert isinstance(provider, OllamaProvider)
        finally:
            if old_anthropic is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = old_anthropic
            if old_google is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = old_google
