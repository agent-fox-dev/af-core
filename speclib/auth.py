"""Anthropic client factory with auth method autodetection.

Creates the appropriate Anthropic SDK client based on configuration:
``Anthropic`` for API key auth, ``AnthropicBedrock`` for AWS Bedrock,
or ``AnthropicVertex`` for Google Vertex AI. Implementation will be
completed in task group 3.
"""

from __future__ import annotations

import anthropic

from speclib.config import SpecToolConfig


def create_client(
    config: SpecToolConfig | None = None,
) -> tuple[
    anthropic.Anthropic | anthropic.AnthropicBedrock | anthropic.AnthropicVertex,
    str,
]:
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
    raise NotImplementedError("create_client not yet implemented")
