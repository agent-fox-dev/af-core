"""Coder: spec-driven coding agent with multi-LLM provider support."""

from coder.config import CoderConfig, load_config
from coder.errors import (
    CoderError,
    ConfigError,
    DependencyCycleError,
    ProviderConfigError,
    ProviderConnectionError,
    SpecParseError,
    TemplateNotFoundError,
    TemplateSecurityError,
)
from coder.logging import get_logger, setup_logging
from coder.models import ExecutionPlan, ParsedSpec

__all__ = [
    # Config
    "CoderConfig",
    "load_config",
    # Logging
    "setup_logging",
    "get_logger",
    # Models
    "ParsedSpec",
    "ExecutionPlan",
    # Exceptions
    "CoderError",
    "ConfigError",
    "DependencyCycleError",
    "ProviderConfigError",
    "ProviderConnectionError",
    "SpecParseError",
    "TemplateNotFoundError",
    "TemplateSecurityError",
]
