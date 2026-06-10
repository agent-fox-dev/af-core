"""Anthropic client factory with auth method autodetection.

Creates the appropriate async Anthropic SDK client based on configuration:
``AsyncAnthropic`` for API key auth, ``AsyncAnthropicBedrock`` for AWS
Bedrock, or ``AsyncAnthropicVertex`` for Google Vertex AI.
"""

from __future__ import annotations

import os
from typing import Union

import anthropic

from speclib.config import SpecToolConfig, load_config
from speclib.errors import ConfigError

_VALID_AUTH_METHODS = ("api_key", "bedrock", "vertex")

ClientType = Union[
    anthropic.AsyncAnthropic,
    anthropic.AsyncAnthropicBedrock,
    anthropic.AsyncAnthropicVertex,
]


def create_client(
    config: SpecToolConfig | None = None,
) -> tuple[ClientType, str]:
    """Create an Anthropic client based on configuration.

    Args:
        config: Optional configuration. If not provided, ``load_config()``
            is called to resolve configuration from YAML and env vars.

    Returns:
        A tuple of ``(client, model_name)`` where *client* is the
        appropriate Anthropic SDK client instance and *model_name* is
        the resolved model identifier.

    Raises:
        ConfigError: If the auth method is unrecognized, the API key is
            missing, or required Vertex environment variables are not set.
    """
    if config is None:
        config = load_config()

    # Resolve auth method: env var overrides config
    auth_method = os.environ.get("AF_SPEC_AUTH", config.auth_method)

    if auth_method not in _VALID_AUTH_METHODS:
        msg = (
            f"Unknown auth method {auth_method!r}. "
            f"Valid methods: {', '.join(_VALID_AUTH_METHODS)}"
        )
        raise ConfigError(msg)

    client: ClientType
    if auth_method == "api_key":
        client = _create_api_key_client(config)
    elif auth_method == "bedrock":
        client = _create_bedrock_client()
    else:  # vertex
        client = _create_vertex_client(config)

    return client, config.model


def _create_api_key_client(
    config: SpecToolConfig,
) -> anthropic.AsyncAnthropic:
    """Create an async Anthropic client using an API key.

    Checks ANTHROPIC_API_KEY env var first, then falls back to the config.

    Raises:
        ConfigError: If no API key is available.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", config.api_key)
    if not api_key:
        msg = (
            "API key required for api_key auth method. "
            "Set the ANTHROPIC_API_KEY environment variable or "
            "configure spec_tool.auth.api_key in "
            "~/.af/settings.yaml."
        )
        raise ConfigError(msg)
    return anthropic.AsyncAnthropic(api_key=api_key)


def _create_bedrock_client() -> anthropic.AsyncAnthropicBedrock:
    """Create an async AnthropicBedrock client using AWS credentials.

    Uses the standard boto3 credential chain from the environment.
    """
    return anthropic.AsyncAnthropicBedrock()


def _create_vertex_client(
    config: SpecToolConfig,
) -> anthropic.AsyncAnthropicVertex:
    """Create an async AnthropicVertex client using GCP credentials.

    Requires AF_SPEC_VERTEX_PROJECT and AF_SPEC_VERTEX_REGION env vars
    or corresponding config values.

    Raises:
        ConfigError: If the project ID is not available.
    """
    project = os.environ.get(
        "AF_SPEC_VERTEX_PROJECT", config.vertex_project
    )
    region = os.environ.get(
        "AF_SPEC_VERTEX_REGION", config.vertex_region
    )

    if not project:
        msg = (
            "Vertex AI project required for vertex auth method. "
            "Set the AF_SPEC_VERTEX_PROJECT environment variable "
            "or configure spec_tool.auth.vertex_project in "
            "~/.af/settings.yaml."
        )
        raise ConfigError(msg)

    if region:
        return anthropic.AsyncAnthropicVertex(
            project_id=project, region=region
        )
    return anthropic.AsyncAnthropicVertex(project_id=project)
