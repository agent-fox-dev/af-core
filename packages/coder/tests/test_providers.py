"""Tests for LLM provider abstraction.

Test Spec Entries: TS-12-3, TS-12-4, TS-12-5, TS-12-6, TS-12-21,
TS-12-E1, TS-12-E12.
"""

from __future__ import annotations

import pytest
from coder.errors import ProviderConfigError, ProviderConnectionError
from coder.providers import (
    AnthropicProvider,
    GoogleProvider,
    LLMProvider,
    OllamaProvider,
)


class TestProviderInterface:
    """Tests for the LLMProvider interface contract."""

    def test_llmprovider_interface(self) -> None:
        """TS-12-21: LLMProvider interface exposes required methods.

        Requirement: 12-REQ-2.1
        Verifies LLMProvider defines model_name, invoke, and validate.
        """
        assert hasattr(LLMProvider, "model_name")
        assert hasattr(LLMProvider, "invoke")
        assert hasattr(LLMProvider, "validate")


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_anthropic_wraps_chat(
        self, fake_anthropic_key: str
    ) -> None:
        """TS-12-3: AnthropicProvider wraps ChatAnthropic.

        Requirement: 12-REQ-2.2
        Verifies AnthropicProvider creates a ChatAnthropic instance.
        """
        from langchain_anthropic import ChatAnthropic

        provider = AnthropicProvider("claude-opus-4-6")
        assert isinstance(provider._chat_model, ChatAnthropic)
        assert provider.model_name == "claude-opus-4-6"


class TestGoogleProvider:
    """Tests for GoogleProvider."""

    def test_google_wraps_chat(
        self, fake_google_key: str
    ) -> None:
        """TS-12-4: GoogleProvider wraps ChatGoogleGenerativeAI.

        Requirement: 12-REQ-2.3
        Verifies GoogleProvider creates a ChatGoogleGenerativeAI instance.
        """
        from langchain_google_genai import ChatGoogleGenerativeAI

        provider = GoogleProvider("gemini-2.5-pro")
        assert isinstance(
            provider._chat_model, ChatGoogleGenerativeAI
        )
        assert provider.model_name == "gemini-2.5-pro"


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_ollama_wraps_chat(self) -> None:
        """TS-12-5: OllamaProvider wraps ChatOllama.

        Requirement: 12-REQ-2.4
        Verifies OllamaProvider creates a ChatOllama instance.
        """
        from langchain_ollama import ChatOllama

        provider = OllamaProvider("codestral:latest")
        assert isinstance(provider._chat_model, ChatOllama)
        assert provider.model_name == "codestral:latest"


class TestCredentialValidation:
    """Tests for provider credential validation."""

    def test_credential_validation(
        self,
        clean_coder_env: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-12-6 / TS-12-E12: Provider validates credentials on construction.

        Requirement: 12-REQ-2.5, 12-REQ-2.E2
        Verifies providers check for required credentials and raise
        ProviderConfigError when API keys are missing.
        """
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ProviderConfigError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider("claude-opus-4-6")

    def test_google_credential_validation(
        self,
        clean_coder_env: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-12-6 (Google variant): Google provider validates credentials.

        Requirement: 12-REQ-2.5, 12-REQ-2.E2
        Verifies GoogleProvider raises ProviderConfigError when
        GOOGLE_API_KEY is missing.
        """
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ProviderConfigError, match="GOOGLE_API_KEY"):
            GoogleProvider("gemini-2.5-pro")


class TestProviderEdgeCases:
    """Edge case tests for providers."""

    def test_ollama_unreachable(self) -> None:
        """TS-12-E1: Ollama server unreachable.

        Requirement: 12-REQ-2.E1
        Verifies clear error when Ollama is not running.
        """
        provider = OllamaProvider(
            "codestral:latest",
            ollama_url="http://localhost:99999",
        )
        with pytest.raises(ProviderConnectionError):
            provider.validate()
