"""Tests for project scaffold and package structure.

Test Spec Entries: TS-01-1 through TS-01-6, TS-01-16, TS-01-17, TS-01-E7.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestProjectStructure:
    """Tests for pyproject.toml and build configuration."""

    def test_ts01_1_package_installable(self) -> None:
        """TS-01-1: Package declares af-spec CLI entry point.

        Requirement: 01-REQ-1.1
        Verifies pyproject.toml declares an af-spec entry point so that
        ``uv pip install .`` produces a working ``af-spec`` CLI command.
        """
        pyproject = PROJECT_ROOT / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml must exist"
        with open(pyproject, "rb") as f:
            toml = tomllib.load(f)
        scripts = toml.get("project", {}).get("scripts", {})
        assert "af-spec" in scripts, "af-spec CLI entry point must be declared"

    def test_ts01_2_runtime_deps(self) -> None:
        """TS-01-2: pyproject.toml declares required runtime dependencies.

        Requirement: 01-REQ-1.2
        Dependencies: afspec, anthropic, click, pyyaml
        """
        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            toml = tomllib.load(f)
        deps = toml.get("project", {}).get("dependencies", [])
        deps_lower = " ".join(deps).lower()
        assert "afspec" in deps_lower, "afspec must be a runtime dependency"
        assert "anthropic" in deps_lower, "anthropic must be a runtime dependency"
        assert "click" in deps_lower, "click must be a runtime dependency"
        assert "pyyaml" in deps_lower, "pyyaml must be a runtime dependency"

    def test_ts01_3_dev_deps(self) -> None:
        """TS-01-3: pyproject.toml declares dev dependencies.

        Requirement: 01-REQ-1.3
        Dev dependencies: pytest, hypothesis, ruff, mypy
        """
        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            toml = tomllib.load(f)

        # Check both possible locations for dev deps
        dev_deps: list[str] = []
        optional_deps = toml.get("project", {}).get("optional-dependencies", {})
        if "dev" in optional_deps:
            dev_deps = optional_deps["dev"]
        dep_groups = toml.get("dependency-groups", {})
        if "dev" in dep_groups:
            dev_deps = dep_groups["dev"]

        deps_lower = " ".join(str(d) for d in dev_deps).lower()
        assert "pytest" in deps_lower, "pytest must be a dev dependency"
        assert "hypothesis" in deps_lower, "hypothesis must be a dev dependency"
        assert "ruff" in deps_lower, "ruff must be a dev dependency"
        assert "mypy" in deps_lower, "mypy must be a dev dependency"

    def test_ts01_4_python_version(self) -> None:
        """TS-01-4: pyproject.toml requires Python 3.14+.

        Requirement: 01-REQ-1.4
        """
        pyproject = PROJECT_ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            toml = tomllib.load(f)
        requires_python = toml.get("project", {}).get("requires-python", "")
        assert requires_python == ">=3.14", (
            f"requires-python must be '>=3.14', got '{requires_python}'"
        )

    def test_ts01_5_make_check(self) -> None:
        """TS-01-5: make check runs linter and tests.

        Requirement: 01-REQ-1.5
        """
        makefile = PROJECT_ROOT / "Makefile"
        assert makefile.exists(), "Makefile must exist"
        content = makefile.read_text()
        has_lint = "ruff" in content or "lint" in content
        has_test = "pytest" in content or "test" in content
        assert has_lint, "Makefile check target must reference ruff or lint"
        assert has_test, "Makefile check target must reference pytest or test"

    def test_ts01_6_make_test(self) -> None:
        """TS-01-6: make test runs pytest.

        Requirement: 01-REQ-1.6
        """
        makefile = PROJECT_ROOT / "Makefile"
        assert makefile.exists(), "Makefile must exist"
        content = makefile.read_text()
        assert "uv run pytest" in content, (
            "Makefile test target must run 'uv run pytest'"
        )


class TestExceptionHierarchy:
    """Tests for speclib exception classes."""

    def test_ts01_16_speclib_error_base(self) -> None:
        """TS-01-16: SpeclibError is defined and inherits from Exception.

        Requirement: 01-REQ-4.1
        """
        from speclib.errors import SpeclibError

        assert issubclass(SpeclibError, Exception)

    def test_ts01_17_config_error_inherits(self) -> None:
        """TS-01-17: ConfigError inherits from SpeclibError.

        Requirement: 01-REQ-4.2
        """
        from speclib.errors import ConfigError, SpeclibError

        assert issubclass(ConfigError, SpeclibError)


class TestEdgeCases:
    """Edge case tests for project scaffold."""

    def test_ts01_e7_uv_required(self) -> None:
        """TS-01-E7: Project documents uv as required installer.

        Requirement: 01-REQ-1.E1
        Verifies that README.md mentions uv and does not include bare
        ``pip install`` instructions (``uv pip install`` is acceptable).
        """
        readme = PROJECT_ROOT / "README.md"
        assert readme.exists(), "README.md must exist"
        content = readme.read_text()
        assert "uv" in content, "README must mention uv as required tool"
        # Ensure no bare pip install instructions (uv pip install is OK)
        for line in content.split("\n"):
            if "pip install" in line and "uv pip install" not in line:
                msg = (
                    f"README should not have bare pip install instructions: {line}"
                )
                raise AssertionError(msg)
