"""Tests for the af-spec CLI commands.

Test Spec Entries: TS-04-1 through TS-04-51, TS-04-P1 through TS-04-P5,
TS-04-SMOKE-1 through TS-04-SMOKE-4.

Tests use Click's CliRunner for isolated CLI invocation. Business logic
(Campaign, SpecSession) is mocked in unit tests. Integration smoke tests
use real instances on temp directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from speclib.cli import main  # noqa: I001

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cli_runner() -> CliRunner:
    """Create a Click CliRunner for isolated command invocation."""
    return CliRunner()


@pytest.fixture()
def campaign_dir(tmp_path: Path) -> Path:
    """Create a temp campaign directory with campaign.yaml."""
    campaign_yaml = tmp_path / "campaign.yaml"
    campaign_yaml.write_text(
        "name: test-campaign\ndescription: A test campaign\n"
    )
    return tmp_path


@pytest.fixture()
def campaign_dir_with_specs(campaign_dir: Path) -> Path:
    """Create a campaign directory with two spec subdirectories."""
    spec_01 = campaign_dir / "01_data_models"
    spec_01.mkdir()
    session_01 = spec_01 / "_session.json"
    session_01.write_text(json.dumps({
        "state": "generated",
        "mode": "interactive",
        "assessment_count": 2,
        "qa_count": 3,
    }))
    prd_01 = spec_01 / "prd.md"
    prd_01.write_text("# Data Models PRD\n\nSome content.")

    spec_02 = campaign_dir / "02_api_endpoints"
    spec_02.mkdir()
    session_02 = spec_02 / "_session.json"
    session_02.write_text(json.dumps({
        "state": "refining",
        "mode": "interactive",
        "assessment_count": 1,
        "qa_count": 0,
    }))
    prd_02 = spec_02 / "prd.md"
    prd_02.write_text("# API Endpoints PRD\n\nSome content.")

    return campaign_dir


@pytest.fixture()
def prd_file(tmp_path: Path) -> Path:
    """Create a temporary PRD file."""
    prd = tmp_path / "prd.md"
    prd.write_text("# Test PRD\n\nSome content for the PRD.")
    return prd


@pytest.fixture()
def answers_file(tmp_path: Path) -> Path:
    """Create a temporary JSON answers file."""
    answers = tmp_path / "answers.json"
    answers.write_text(
        json.dumps({"q1": "answer1", "q2": "answer2"})
    )
    return answers


@pytest.fixture()
def bad_json_file(tmp_path: Path) -> Path:
    """Create a temporary file with invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    return bad


@pytest.fixture()
def bad_schema_file(tmp_path: Path) -> Path:
    """Create a file with wrong schema (list instead of dict)."""
    bad = tmp_path / "bad_schema.json"
    bad.write_text(json.dumps(["not", "an", "object"]))
    return bad


def _mock_campaign(
    specs: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock Campaign with optional spec list.

    Each spec dict should have keys: name, number, state,
    artifact_count.
    """
    campaign = MagicMock()
    if specs is None:
        specs = []

    spec_dirs = []
    for spec in specs:
        spec_dir = MagicMock()
        spec_dir.name = spec.get("name", "01_test")
        spec_dir.stem = spec_dir.name
        spec_dirs.append(spec_dir)

    campaign.specs.return_value = spec_dirs
    return campaign


def _mock_session(
    state: str = "init",
    mode: str = "interactive",
    assessment_count: int = 0,
    qa_count: int = 0,
    artifacts: list[str] | None = None,
) -> MagicMock:
    """Create a mock SpecSession with configurable state."""
    session = MagicMock()
    session.state = state
    session.mode = mode
    session.assessment_count = assessment_count
    session.qa_count = qa_count
    session.artifacts = artifacts or []
    return session


def _sample_assessment() -> dict[str, Any]:
    """Return a sample assessment result for output formatting."""
    return {
        "quality": "needs_refinement",
        "score": 7,
        "summary": "Good start but needs more detail",
        "gaps": [
            "Missing error handling for edge case X",
            "No mention of performance requirements",
        ],
        "questions": [
            {
                "id": "q1",
                "text": "What is the expected data volume?",
            },
            {
                "id": "q2",
                "text": "Should the API support pagination?",
            },
        ],
    }


def _assert_exit(result: Any, code: int) -> None:
    """Assert CLI result has the expected exit code."""
    actual = result.exit_code
    out = result.output
    assert actual == code, (
        f"Expected exit {code}, got {actual}: {out}"
    )


# ================================================================
# Task 1.2: Campaign command tests (TS-04-1 through TS-04-10)
# ================================================================


class TestInitCommand:
    """Tests for the af-spec init command."""

    def test_init_creates_campaign(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-1: Init creates campaign directory.

        Requirement: 04-REQ-1.1
        Verify af-spec init calls Campaign.create and prints
        confirmation.
        """
        target = tmp_path / "test-campaign"
        with patch(
            "speclib.cli.Campaign"
        ) as mock_cls:
            mock_cls.create.return_value = None
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    str(target),
                    "--name",
                    "Test",
                    "--description",
                    "A test",
                ],
            )
        _assert_exit(result, 0)
        resolved = str(target.resolve())
        assert resolved in result.output or "Test" in result.output
        mock_cls.create.assert_called_once()

    def test_init_defaults_name_to_basename(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-2: Init defaults name to directory basename.

        Requirement: 04-REQ-1.2
        Verify init uses directory basename when --name is omitted.
        """
        target = tmp_path / "my-project"
        with patch(
            "speclib.cli.Campaign"
        ) as mock_cls:
            mock_cls.create.return_value = None
            result = cli_runner.invoke(
                main, ["init", str(target)]
            )
        _assert_exit(result, 0)
        call_args = mock_cls.create.call_args
        args, kwargs = call_args
        all_vals = list(args) + list(kwargs.values())
        assert "my-project" in str(all_vals), (
            f"Expected 'my-project' in call args, got {all_vals}"
        )

    def test_init_defaults_description_empty(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-3: Init defaults description to empty string.

        Requirement: 04-REQ-1.3
        Verify init uses empty description when --description is
        omitted.
        """
        target = tmp_path / "test"
        with patch(
            "speclib.cli.Campaign"
        ) as mock_cls:
            mock_cls.create.return_value = None
            result = cli_runner.invoke(
                main, ["init", str(target), "--name", "Test"]
            )
        _assert_exit(result, 0)
        call_args = mock_cls.create.call_args
        args, kwargs = call_args
        all_vals = list(args) + list(kwargs.values())
        assert "" in all_vals, (
            f"Expected empty string in args, got {call_args}"
        )

    def test_init_handles_campaign_error(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-4: Init handles CampaignError.

        Requirement: 04-REQ-1.4
        Verify init prints error and exits 1 when Campaign.create
        fails.
        """
        from speclib.errors import SpeclibError

        class _CampaignError(SpeclibError):
            pass

        target = tmp_path / "existing"
        with patch(
            "speclib.cli.Campaign"
        ) as mock_cls:
            mock_cls.create.side_effect = _CampaignError(
                "already exists"
            )
            result = cli_runner.invoke(
                main, ["init", str(target)]
            )
        _assert_exit(result, 1)
        combined = result.output + result.stderr
        assert "already exists" in combined

    def test_init_resolves_relative_path(
        self, cli_runner: CliRunner,
    ) -> None:
        """TS-04-5: Init resolves relative path to absolute.

        Requirement: 04-REQ-1.E1
        Verify init resolves a relative path to absolute before
        passing to Campaign.create.
        """
        with patch(
            "speclib.cli.Campaign"
        ) as mock_cls:
            mock_cls.create.return_value = None
            result = cli_runner.invoke(
                main,
                ["init", "./my-campaign", "--name", "Test"],
            )
        _assert_exit(result, 0)
        call_args = mock_cls.create.call_args
        args, kwargs = call_args
        path_arg = args[0] if args else kwargs.get("path")
        assert Path(str(path_arg)).is_absolute(), (
            f"Expected absolute path, got {path_arg}"
        )


class TestListCommand:
    """Tests for the af-spec list command."""

    def test_list_displays_table(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-6: List displays spec table.

        Requirement: 04-REQ-2.1
        Verify list displays a table with spec number, name, state,
        artifacts.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "list",
            ],
        )
        _assert_exit(result, 0)
        assert "01" in result.output
        assert "data_models" in result.output

    def test_list_explicit_directory(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-7: List with explicit directory.

        Requirement: 04-REQ-2.2
        Verify list accepts explicit campaign directory argument.
        """
        result = cli_runner.invoke(
            main, ["list", str(campaign_dir_with_specs)]
        )
        _assert_exit(result, 0)

    def test_list_empty_campaign(
        self, cli_runner: CliRunner, campaign_dir: Path
    ) -> None:
        """TS-04-8: List empty campaign.

        Requirement: 04-REQ-2.3
        Verify list prints empty message for campaign with no specs.
        """
        result = cli_runner.invoke(
            main,
            ["--campaign-dir", str(campaign_dir), "list"],
        )
        _assert_exit(result, 0)
        lower = result.output.lower()
        assert "empty" in lower or "no specs" in lower, (
            f"Expected empty message, got: {result.output}"
        )

    def test_list_sorts_by_prefix(
        self, cli_runner: CliRunner, campaign_dir: Path
    ) -> None:
        """TS-04-9: List sorts by numeric prefix.

        Requirement: 04-REQ-2.4
        Verify specs are sorted by number in list output.
        """
        # Create specs out of order: 03, 01, 02
        for num, name in [(3, "auth"), (1, "data"), (2, "api")]:
            d = campaign_dir / f"{num:02d}_{name}"
            d.mkdir()
            sf = d / "_session.json"
            sf.write_text(json.dumps({"state": "init"}))

        result = cli_runner.invoke(
            main,
            ["--campaign-dir", str(campaign_dir), "list"],
        )
        _assert_exit(result, 0)
        pos_01 = result.output.index("01")
        pos_02 = result.output.index("02")
        pos_03 = result.output.index("03")
        assert pos_01 < pos_02 < pos_03, (
            f"Sorted order: 01@{pos_01} 02@{pos_02} 03@{pos_03}"
        )

    def test_list_error_non_campaign(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-10: List error on non-campaign directory.

        Requirement: 04-REQ-2.E1
        Verify list fails with clear error when not in a campaign
        dir.
        """
        result = cli_runner.invoke(
            main,
            ["--campaign-dir", str(tmp_path), "list"],
        )
        _assert_exit(result, 1)
        combined = (result.output + result.stderr).lower()
        assert "campaign" in combined


# ================================================================
# Task 1.3: Cross-cutting and resolution tests
#            (TS-04-44 through TS-04-51)
# ================================================================


class TestSpecResolution:
    """Tests for spec argument resolution."""

    def test_spec_not_found_lists_available(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-44: Spec not found lists available specs.

        Requirement: 04-REQ-10.E1, 04-REQ-CC.5
        Verify unmatched spec argument lists available specs.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "assess",
                "99",
            ],
        )
        _assert_exit(result, 1)
        combined = result.output + result.stderr
        assert "01" in combined, (
            f"Expected '01' in error, got: {combined}"
        )
        assert "02" in combined, (
            f"Expected '02' in error, got: {combined}"
        )

    def test_spec_resolved_by_full_name(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-47: Spec resolved by full name.

        Requirement: 04-REQ-CC.4
        Verify spec can be resolved by full directory name.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "status",
                "01_data_models",
            ],
        )
        _assert_exit(result, 0)

    def test_spec_resolved_by_number(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-48: Spec resolved by numeric prefix.

        Requirement: 04-REQ-CC.4
        Verify spec can be resolved by just the number.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "status",
                "01",
            ],
        )
        _assert_exit(result, 0)


class TestCampaignDirResolution:
    """Tests for campaign directory resolution."""

    def test_campaign_dir_option_overrides_cwd(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-45: Campaign-dir option overrides CWD.

        Requirement: 04-REQ-CC.1, 04-REQ-CC.2
        Verify --campaign-dir option is used instead of CWD.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "list",
            ],
        )
        _assert_exit(result, 0)
        assert "01" in result.output

    def test_no_campaign_dir_error(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-46: No campaign directory error.

        Requirement: 04-REQ-CC.3
        Verify clear error when not in a campaign directory.
        """
        result = cli_runner.invoke(
            main,
            ["--campaign-dir", str(tmp_path), "status"],
        )
        _assert_exit(result, 1)
        combined = result.output + result.stderr
        assert "campaign" in combined.lower(), (
            f"Expected 'campaign' in error, got: {combined}"
        )
        assert "--campaign-dir" in combined, (
            f"Expected hint in error, got: {combined}"
        )


class TestExitCodes:
    """Tests for exit code conventions."""

    def test_exit_code_0_success(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-49: Exit code 0 on success.

        Requirement: 04-REQ-CC.6
        Verify successful commands exit with code 0.
        """
        result = cli_runner.invoke(
            main,
            [
                "--campaign-dir",
                str(campaign_dir_with_specs),
                "status",
                "01",
            ],
        )
        _assert_exit(result, 0)

    def test_exit_code_1_user_error(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TS-04-50: Exit code 1 on user error.

        Requirement: 04-REQ-CC.6
        Verify user errors exit with code 1.
        """
        result = cli_runner.invoke(
            main,
            ["--campaign-dir", str(tmp_path), "list"],
        )
        _assert_exit(result, 1)

    def test_exit_code_2_internal_error(
        self,
        cli_runner: CliRunner,
        campaign_dir_with_specs: Path,
    ) -> None:
        """TS-04-51: Exit code 2 on internal error.

        Requirement: 04-REQ-CC.6
        Verify unexpected exceptions exit with code 2.
        """
        with patch(
            "speclib.cli.SpecSession"
        ) as mock_cls:
            mock_cls.resume.side_effect = RuntimeError(
                "unexpected"
            )
            result = cli_runner.invoke(
                main,
                [
                    "--campaign-dir",
                    str(campaign_dir_with_specs),
                    "assess",
                    "01",
                ],
            )
        _assert_exit(result, 2)
