"""LLM provider abstraction layer.

Defines the LLMProvider interface and concrete implementations for
Anthropic, Google, and Ollama backends. Each provider wraps a LangChain
chat model and validates credentials at construction time.
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from langchain_core.messages import AIMessage, BaseMessage

from coder.errors import ProviderConfigError, ProviderConnectionError


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the LLM provider interface.

    All providers must implement model_name, invoke(), and validate().
    """

    @property
    def model_name(self) -> str:
        """The model name this provider was configured with."""
        ...

    def invoke(
        self,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
    ) -> AIMessage:
        """Send messages to the LLM, optionally with tool definitions.

        Args:
            messages: List of chat messages to send.
            tools: Optional list of tool definitions.

        Returns:
            The AI's response message.
        """
        ...

    def validate(self) -> None:
        """Verify provider is correctly configured.

        Raises:
            ProviderConfigError: If credentials are missing.
            ProviderConnectionError: If the backend is unreachable.
        """
        ...


class AnthropicProvider:
    """LLM provider wrapping ChatAnthropic from langchain-anthropic.

    Validates that the ANTHROPIC_API_KEY environment variable is set
    at construction time.
    """

    _ENV_VAR = "ANTHROPIC_API_KEY"

    def __init__(self, model_name: str) -> None:
        api_key = os.environ.get(self._ENV_VAR)
        if not api_key:
            raise ProviderConfigError(
                f"Missing required environment variable {self._ENV_VAR}. "
                f"Set {self._ENV_VAR} to your Anthropic API key.",
                env_var=self._ENV_VAR,
            )

        from langchain_anthropic import ChatAnthropic

        self._model_name = model_name
        self._chat_model = ChatAnthropic(
            model_name=model_name,
            api_key=api_key,  # type: ignore[arg-type]
        )  # type: ignore[call-arg]

    @property
    def model_name(self) -> str:
        """The model name this provider was configured with."""
        return self._model_name

    def invoke(
        self,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
    ) -> AIMessage:
        """Send messages to the Anthropic LLM.

        Args:
            messages: List of chat messages to send.
            tools: Optional list of tool definitions.

        Returns:
            The AI's response message.
        """
        if tools:
            model = self._chat_model.bind_tools(tools)
        else:
            model = self._chat_model
        return model.invoke(messages)  # type: ignore[return-value]

    def validate(self) -> None:
        """Verify Anthropic credentials are configured.

        Raises:
            ProviderConfigError: If the API key is missing.
        """
        if not os.environ.get(self._ENV_VAR):
            raise ProviderConfigError(
                f"Missing required environment variable {self._ENV_VAR}.",
                env_var=self._ENV_VAR,
            )


class GoogleProvider:
    """LLM provider wrapping ChatGoogleGenerativeAI.

    Validates that the GOOGLE_API_KEY environment variable is set
    at construction time.
    """

    _ENV_VAR = "GOOGLE_API_KEY"

    def __init__(self, model_name: str) -> None:
        api_key = os.environ.get(self._ENV_VAR)
        if not api_key:
            raise ProviderConfigError(
                f"Missing required environment variable {self._ENV_VAR}. "
                f"Set {self._ENV_VAR} to your Google API key.",
                env_var=self._ENV_VAR,
            )

        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model_name = model_name
        self._chat_model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,  # type: ignore[arg-type]
        )

    @property
    def model_name(self) -> str:
        """The model name this provider was configured with."""
        return self._model_name

    def invoke(
        self,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
    ) -> AIMessage:
        """Send messages to the Google LLM.

        Args:
            messages: List of chat messages to send.
            tools: Optional list of tool definitions.

        Returns:
            The AI's response message.
        """
        if tools:
            model = self._chat_model.bind_tools(tools)
        else:
            model = self._chat_model
        return model.invoke(messages)  # type: ignore[return-value]

    def validate(self) -> None:
        """Verify Google credentials are configured.

        Raises:
            ProviderConfigError: If the API key is missing.
        """
        if not os.environ.get(self._ENV_VAR):
            raise ProviderConfigError(
                f"Missing required environment variable {self._ENV_VAR}.",
                env_var=self._ENV_VAR,
            )


class OllamaProvider:
    """LLM provider wrapping ChatOllama from langchain-ollama.

    Does not require API keys. The validate() method checks that the
    Ollama server is reachable at the configured URL.
    """

    def __init__(
        self,
        model_name: str,
        *,
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        from langchain_ollama import ChatOllama

        self._model_name = model_name
        self._ollama_url = ollama_url
        self._chat_model = ChatOllama(
            model=model_name,
            base_url=ollama_url,
        )

    @property
    def model_name(self) -> str:
        """The model name this provider was configured with."""
        return self._model_name

    def invoke(
        self,
        messages: list[BaseMessage],
        tools: list[Any] | None = None,
    ) -> AIMessage:
        """Send messages to the Ollama LLM.

        Args:
            messages: List of chat messages to send.
            tools: Optional list of tool definitions.

        Returns:
            The AI's response message.
        """
        if tools:
            model = self._chat_model.bind_tools(tools)
        else:
            model = self._chat_model
        return model.invoke(messages)  # type: ignore[return-value]

    def validate(self) -> None:
        """Validate Ollama server connectivity.

        Checks that the Ollama server is reachable by making an HTTP
        request to its base URL.

        Raises:
            ProviderConnectionError: If the server is unreachable.
        """
        try:
            httpx.get(self._ollama_url, timeout=5.0)
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            raise ProviderConnectionError(
                f"Cannot connect to Ollama server at {self._ollama_url}: "
                f"{exc}",
                url=self._ollama_url,
            ) from exc
