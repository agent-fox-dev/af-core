"""speclib — AI-powered spec creation tool.

Re-exports key types from submodules for convenient access.
"""

from __future__ import annotations

from speclib.errors import ConfigError, SpeclibError

__all__ = [
    "ConfigError",
    "SpeclibError",
]
