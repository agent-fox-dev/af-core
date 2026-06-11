"""Structural tests for the speclib library package.

Verifies file existence, pyproject.toml content, and package structure
after the monorepo restructure.

Test Spec Entries: TS-10-1, TS-10-2, TS-10-14, TS-10-15, TS-10-E7
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPECLIB_PKG = REPO_ROOT / "packages" / "speclib"


# ---------------------------------------------------------------------------
# TS-10-1: Library Package Directory Structure
# Requirement: 10-REQ-1.3
# ---------------------------------------------------------------------------

_EXPECTED_MODULES = [
    "__init__.py",
    "agent.py",
    "auth.py",
    "campaign.py",
    "config.py",
    "errors.py",
    "prompts.py",
    "session.py",
    "tools.py",
]


@pytest.mark.parametrize("module", _EXPECTED_MODULES)
def test_ts10_1_library_module_exists(module: str) -> None:
    """TS-10-1: Each required library module exists at packages/speclib/speclib/."""
    path = SPECLIB_PKG / "speclib" / module
    assert path.exists(), f"Expected module not found: {path}"


# ---------------------------------------------------------------------------
# TS-10-2: Library pyproject.toml Dependencies
# Requirement: 10-REQ-1.2
# ---------------------------------------------------------------------------


def _load_speclib_pyproject() -> dict:
    """Load and parse packages/speclib/pyproject.toml."""
    pyproject_path = SPECLIB_PKG / "pyproject.toml"
    assert pyproject_path.exists(), (
        f"pyproject.toml not found at {pyproject_path}"
    )
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def test_ts10_2_dependencies_include_required_libs() -> None:
    """TS-10-2: speclib dependencies include afspec, anthropic, pyyaml."""
    config = _load_speclib_pyproject()
    deps = config["project"]["dependencies"]

    assert any("afspec" in d for d in deps), "afspec not in dependencies"
    assert any("anthropic" in d for d in deps), "anthropic not in dependencies"
    assert any("pyyaml" in d.lower() for d in deps), "pyyaml not in dependencies"


def test_ts10_2_no_cli_dependencies() -> None:
    """TS-10-2: speclib dependencies must NOT include click or rich."""
    config = _load_speclib_pyproject()
    deps = config["project"]["dependencies"]

    assert not any("click" in d.lower() for d in deps), (
        "click should not be in speclib dependencies"
    )
    assert not any("rich" in d.lower() for d in deps), (
        "rich should not be in speclib dependencies"
    )


# ---------------------------------------------------------------------------
# TS-10-14: Library Package Has afspec Path Dependency
# Requirement: 10-REQ-1.4
# ---------------------------------------------------------------------------


def test_ts10_14_afspec_path_dependency() -> None:
    """TS-10-14: speclib declares afspec as a path dependency to ../afspec."""
    config = _load_speclib_pyproject()
    sources = config["tool"]["uv"]["sources"]

    assert "afspec" in sources, "afspec not in uv sources"
    assert sources["afspec"]["path"] == "../afspec", (
        f"afspec path should be ../afspec, got {sources['afspec'].get('path')}"
    )


# ---------------------------------------------------------------------------
# TS-10-15: Library Dev Dependencies
# Requirement: 10-REQ-1.5
# ---------------------------------------------------------------------------


def test_ts10_15_dev_dependencies() -> None:
    """TS-10-15: speclib has dev optional-dependencies with test/lint tools."""
    config = _load_speclib_pyproject()
    dev_deps = config["project"]["optional-dependencies"]["dev"]

    assert any("pytest" in d for d in dev_deps), "pytest not in dev deps"
    assert any("ruff" in d for d in dev_deps), "ruff not in dev deps"
    assert any("mypy" in d for d in dev_deps), "mypy not in dev deps"


# ---------------------------------------------------------------------------
# TS-10-E7: Cross-Package Test Isolation
# Requirement: 10-REQ-4.E1
# ---------------------------------------------------------------------------


def test_ts10_e7_no_spec_cli_imports_in_speclib_tests() -> None:
    """TS-10-E7: No speclib test file imports from spec_cli."""
    test_dir = SPECLIB_PKG / "tests"
    assert test_dir.exists(), f"Test directory not found: {test_dir}"

    for test_file in test_dir.glob("*.py"):
        source = test_file.read_text()
        assert "from spec_cli" not in source, (
            f"{test_file.name} imports from spec_cli"
        )
        assert "import spec_cli" not in source, (
            f"{test_file.name} imports spec_cli"
        )
