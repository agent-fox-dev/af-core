"""Configuration loading from YAML and environment variables.

Reads ``~/.af/settings.yaml`` and environment variables to produce a
``SpecToolConfig``. Implementation will be completed in task group 3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpecToolConfig:
    """Resolved configuration for the spec tool.

    Attributes:
        model: The Anthropic model to use.
        auth_method: Authentication method (``api_key``, ``bedrock``, or ``vertex``).
        api_key: Anthropic API key (for ``api_key`` auth method).
        vertex_project: GCP project ID (for ``vertex`` auth method).
        vertex_region: GCP region (for ``vertex`` auth method).
    """

    model: str = "claude-sonnet-4-6"
    auth_method: str = "api_key"
    api_key: str | None = None
    vertex_project: str | None = None
    vertex_region: str | None = None


def load_config() -> SpecToolConfig:
    """Load configuration from ``~/.af/settings.yaml`` and env vars.

    Reads the ``spec_tool`` section from the settings file, then applies
    environment variable overrides. Returns a ``SpecToolConfig`` with
    resolved values.

    Raises:
        ConfigError: If the settings file contains invalid YAML.
    """
    raise NotImplementedError("load_config not yet implemented")
