"""Integration smoke tests for the monorepo restructure.

Verifies end-to-end execution paths through the CLI and library,
confirming that the full chain works after the restructure.

Test Spec Entries: TS-10-SMOKE-1, TS-10-SMOKE-2
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# TS-10-SMOKE-1: spec new Creates Spec Directory
# Execution Path 1 from design.md
# ---------------------------------------------------------------------------


def test_ts10_smoke1_spec_new_creates_spec_directory(tmp_path: Path) -> None:
    """TS-10-SMOKE-1: spec new creates spec directory via full CLI chain.

    End-to-end test: CLI -> speclib.campaign -> speclib.session -> filesystem.
    Must NOT mock Campaign, SpecSession, or filesystem operations.
    """
    try:
        from spec_cli.cli import main
    except ImportError:
        pytest.fail("spec_cli.cli is not importable - spec-cli package not installed")

    from click.testing import CliRunner

    from speclib import Campaign

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        Campaign.create(Path(td), "test", "")
        Path(td, "prd.md").write_text("# Test PRD\n\nThis is a test PRD.")

        result = runner.invoke(
            main,
            ["new", "prd.md", "--name", "test_spec"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0, (
            f"spec new failed with exit code {result.exit_code}:\n"
            f"{result.output}"
        )
        spec_dir = Path(td) / ".specs" / "01_test_spec"
        assert spec_dir.exists(), (
            f"Spec directory not created at {spec_dir}"
        )
        assert (spec_dir / "prd.md").exists(), (
            "prd.md not found in spec directory"
        )
        assert (spec_dir / "_session.json").exists(), (
            "_session.json not found in spec directory"
        )


# ---------------------------------------------------------------------------
# TS-10-SMOKE-2: Library Used Without CLI
# Execution Path 3 from design.md
# ---------------------------------------------------------------------------


def test_ts10_smoke2_library_without_cli(tmp_path: Path) -> None:
    """TS-10-SMOKE-2: speclib works programmatically without CLI.

    Must NOT import spec_cli anywhere in this test.
    """
    # Clear click/rich from sys.modules to verify they aren't loaded
    saved_click = sys.modules.pop("click", None)
    saved_rich = sys.modules.pop("rich", None)

    try:
        from speclib import Campaign

        campaign = Campaign.create(tmp_path, "test", "test campaign")
        session = campaign.new_spec("my_spec", "# Test PRD")

        assert session.spec_dir.exists(), "Spec directory was not created"
        assert (session.spec_dir / "prd.md").exists(), (
            "prd.md not found in spec directory"
        )
        assert "click" not in sys.modules, (
            "click was imported during library-only usage"
        )
    finally:
        if saved_click is not None:
            sys.modules["click"] = saved_click
        if saved_rich is not None:
            sys.modules["rich"] = saved_rich
