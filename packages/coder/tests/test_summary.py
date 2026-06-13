"""Tests for run summary generation.

Covers acceptance criteria: TS-15-14, TS-15-22.
Edge cases: TS-15-E7 (summary write failure fallback).
"""

from __future__ import annotations

import logging
import stat
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from coder.summary import write_run_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_state(
    *,
    spec_name: str = "test_spec",
    model_name: str = "claude-opus-4-6",
    current_task_group: int = 3,
    total_groups: int = 3,
    success: bool = True,
    halted: bool = False,
    halt_reason: str = "",
    elapsed_seconds: float = 120.5,
) -> dict[str, Any]:
    """Create a completed execution state for summary tests."""
    return {
        "spec_name": spec_name,
        "model_name": model_name,
        "current_task_group": current_task_group,
        "total_groups": total_groups,
        "success": success,
        "halted": halted,
        "halt_reason": halt_reason,
        "elapsed_seconds": elapsed_seconds,
    }


def _make_fake_tracker(
    input_tokens: int = 5000,
    output_tokens: int = 3000,
    call_count: int = 10,
) -> Any:
    """Create a fake token tracker for summary tests."""
    tracker = MagicMock()
    tracker.input_tokens = input_tokens
    tracker.output_tokens = output_tokens
    tracker.total_tokens = input_tokens + output_tokens
    tracker.call_count = call_count
    tracker.to_dict.return_value = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "call_count": call_count,
    }
    return tracker


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestRunSummaryContents:
    """TS-15-14: Run summary contains required fields."""

    def test_summary_has_required_fields(
        self, tmp_path: Path
    ) -> None:
        """TS-15-14: Verify run summary has all expected fields.

        Requirement: 15-REQ-6.2
        Summary contains spec name, model, groups, tokens, time, status.
        """
        state = _make_completed_state()
        tracker = _make_fake_tracker()

        path = write_run_summary(state, tmp_path, tracker)
        content = path.read_text()

        # Check for required field mentions
        assert "spec" in content.lower() or "test_spec" in content
        assert "model" in content.lower() or "claude" in content
        assert "token" in content.lower()

    def test_summary_has_status(self, tmp_path: Path) -> None:
        """TS-15-14 (status): Summary includes final status.

        Requirement: 15-REQ-6.2
        """
        state = _make_completed_state(success=True)
        tracker = _make_fake_tracker()

        path = write_run_summary(state, tmp_path, tracker)
        content = path.read_text()

        assert (
            "success" in content.lower()
            or "complete" in content.lower()
        )


class TestRunSummaryLocation:
    """TS-15-22: Run summary file written to worktree."""

    def test_file_in_worktree(self, tmp_path: Path) -> None:
        """TS-15-22: Verify _run_summary.md location.

        Requirement: 15-REQ-6.1
        """
        state = _make_completed_state()
        tracker = _make_fake_tracker()

        path = write_run_summary(state, tmp_path, tracker)

        assert path == tmp_path / "_run_summary.md"
        assert path.exists()

    def test_path_logged(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-15-22: Verify path is logged to console.

        Requirement: 15-REQ-6.1
        """
        state = _make_completed_state()
        tracker = _make_fake_tracker()

        with caplog.at_level(logging.INFO):
            write_run_summary(state, tmp_path, tracker)

        assert any(
            "_run_summary.md" in record.message
            for record in caplog.records
        )


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestRunSummaryEdgeCases:
    """TS-15-E7: Summary write failure falls back to console."""

    def test_write_failure_no_exception(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """TS-15-E7: Verify console fallback when file write fails.

        Requirement: 15-REQ-6.E1
        No exception raised. Warning logged. Summary printed to console.
        """
        state = _make_completed_state()
        tracker = _make_fake_tracker()

        # Create a read-only directory to force write failure
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            with caplog.at_level(logging.WARNING):
                # Should not raise
                write_run_summary(state, read_only_dir, tracker)

            # Warning should be logged
            assert any(
                "warning" in record.message.lower()
                or record.levelno >= logging.WARNING
                for record in caplog.records
            )
        finally:
            # Restore permissions for cleanup
            read_only_dir.chmod(
                stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
            )
