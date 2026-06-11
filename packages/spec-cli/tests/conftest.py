"""Shared pytest configuration for spec-cli tests."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: integration tests (may be slow or modify env)",
    )
