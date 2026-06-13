"""Shared test fixtures for coder package tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for config tests."""
    return tmp_path


@pytest.fixture()
def campaign_dir(tmp_path: Path) -> Path:
    """Create a temporary campaign directory with required structure."""
    campaign = tmp_path / "test_campaign"
    campaign.mkdir()
    return campaign


@pytest.fixture()
def clean_coder_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all CODER_* and provider API key env vars.

    Ensures test isolation from host environment variables that could
    affect configuration loading or provider creation.
    """
    keys_to_remove = [
        k
        for k in os.environ
        if k.startswith("CODER_")
        or k in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
    ]
    for key in keys_to_remove:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def fake_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set a fake Anthropic API key for testing.

    Returns the fake key value for assertions.
    """
    key = "sk-ant-test-key-12345"
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    return key


@pytest.fixture()
def fake_google_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set a fake Google API key for testing.

    Returns the fake key value for assertions.
    """
    key = "google-test-key-12345"
    monkeypatch.setenv("GOOGLE_API_KEY", key)
    return key


@pytest.fixture()
def template_dir(tmp_path: Path) -> Path:
    """Create a project-level template directory.

    Returns the path to .coder/templates/ within the temporary directory.
    """
    tpl_dir = tmp_path / ".coder" / "templates"
    tpl_dir.mkdir(parents=True)
    return tpl_dir
