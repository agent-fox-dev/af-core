"""Tests for post-mortem generation, graceful shutdown, and worktree handling.

Covers acceptance criteria: TS-15-9, TS-15-10, TS-15-13, TS-15-17, TS-15-21.
Edge cases: TS-15-E4 (post-mortem to cwd when no worktree).
Property tests: TS-15-P3 (post-mortem section completeness).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from coder.postmortem import (
    generate_postmortem,
    generate_postmortem_node,
    perform_graceful_shutdown,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "## Summary",
    "## Halt Reason",
    "## Execution Context",
    "## Attempt History",
    "## Last Test Output",
    "## Token Usage",
    "## Recommendations",
]


def _make_halted_state(
    *,
    halt_reason: str = "Max attempts exceeded",
    spec_name: str = "test_spec",
    model_name: str = "claude-opus-4-6",
    current_phase: str = "implement",
    current_task_group: int = 2,
    total_groups: int = 4,
    attempt_count: int = 5,
    max_attempts: int = 5,
    test_results: str = "FAIL: 3 failed, 2 passed",
) -> dict[str, Any]:
    """Create a halted state fixture for post-mortem tests."""
    return {
        "halted": True,
        "halt_reason": halt_reason,
        "spec_name": spec_name,
        "model_name": model_name,
        "current_phase": current_phase,
        "current_task_group": current_task_group,
        "total_groups": total_groups,
        "attempt_count": attempt_count,
        "max_attempts": max_attempts,
        "test_results": test_results,
        "history": [
            {
                "phase": "understand_spec",
                "task_group": 1,
                "attempt": 0,
                "timestamp": "2026-01-01T10:00:01",
                "result": "ok",
            },
            {
                "phase": "implement",
                "task_group": 2,
                "attempt": 5,
                "timestamp": "2026-01-01T10:05:00",
                "result": "fail",
            },
        ],
    }


def _make_fake_tracker(
    input_tokens: int = 5000,
    output_tokens: int = 3000,
    call_count: int = 10,
) -> Any:
    """Create a fake token tracker for post-mortem tests."""
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


class TestPostmortemSections:
    """TS-15-9: Post-mortem contains required sections."""

    def test_all_sections_present(self, tmp_path: Path) -> None:
        """TS-15-9: Verify all post-mortem sections are present.

        Requirement: 15-REQ-3.2
        """
        state = _make_halted_state()
        tracker = _make_fake_tracker()

        path = generate_postmortem(state, tmp_path, tracker)
        content = path.read_text()

        for section in REQUIRED_SECTIONS:
            assert section in content, (
                f"Missing section: {section}"
            )


class TestPostmortemLocation:
    """TS-15-10: Post-mortem written to worktree."""

    def test_file_in_worktree(self, tmp_path: Path) -> None:
        """TS-15-10: Verify post-mortem file location.

        Requirement: 15-REQ-3.1
        """
        state = _make_halted_state()
        tracker = _make_fake_tracker()

        path = generate_postmortem(state, tmp_path, tracker)

        assert path == tmp_path / "_postmortem.md"
        assert path.exists()


class TestPostmortemTerminalNode:
    """TS-15-17: Post-mortem is a terminal graph node."""

    def test_returns_state_unchanged(self, tmp_path: Path) -> None:
        """TS-15-17: generate_postmortem_node returns state unchanged.

        Requirement: 15-REQ-3.3
        Verify:
        1. The post-mortem file is written.
        2. The returned state is identical to the input state.
        """
        state = _make_halted_state()
        # The node reads worktree and tracker from state
        state["worktree"] = str(tmp_path)
        state["token_tracker"] = _make_fake_tracker()

        returned_state = generate_postmortem_node(state)

        # Post-mortem file should be written
        assert (tmp_path / "_postmortem.md").exists()

        # State should be unchanged
        assert returned_state["halted"] is True
        assert returned_state["halt_reason"] == state["halt_reason"]
        assert returned_state["current_phase"] == state["current_phase"]
        assert returned_state["spec_name"] == state["spec_name"]


class TestGracefulShutdown:
    """TS-15-13: Graceful shutdown preserves state."""

    def test_shutdown_creates_run_json(self, tmp_path: Path) -> None:
        """TS-15-13: Verify state is persisted during shutdown.

        Requirement: 15-REQ-5.2
        """
        state = _make_halted_state()
        tracker = _make_fake_tracker()

        perform_graceful_shutdown(state, tmp_path, tracker)

        run_json = tmp_path / "_run.json"
        assert run_json.exists()

    def test_shutdown_creates_postmortem(self, tmp_path: Path) -> None:
        """TS-15-13: Verify post-mortem is generated during shutdown.

        Requirement: 15-REQ-5.2
        """
        state = _make_halted_state()
        tracker = _make_fake_tracker()

        perform_graceful_shutdown(state, tmp_path, tracker)

        postmortem = tmp_path / "_postmortem.md"
        assert postmortem.exists()


class TestWorktreePreservation:
    """TS-15-21: Worktree left intact on shutdown."""

    def test_worktree_intact_after_shutdown(
        self, tmp_path: Path
    ) -> None:
        """TS-15-21: Verify worktree is not merged or deleted.

        Requirement: 15-REQ-5.3
        """
        # Create a file in the worktree to verify it's untouched
        marker_file = tmp_path / "partial_work.py"
        marker_file.write_text("partial")

        state = _make_halted_state()
        tracker = _make_fake_tracker()

        perform_graceful_shutdown(state, tmp_path, tracker)

        assert tmp_path.exists()
        assert marker_file.exists()
        assert marker_file.read_text() == "partial"


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestPostmortemEdgeCases:
    """TS-15-E4: Post-mortem to cwd when no worktree."""

    def test_fallback_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TS-15-E4: Verify fallback to cwd for post-mortem.

        Requirement: 15-REQ-3.E1
        When worktree path does not exist, fall back to cwd.
        """
        monkeypatch.chdir(tmp_path)
        state = _make_halted_state()
        tracker = _make_fake_tracker()

        nonexistent = Path("/nonexistent_worktree_path_12345")
        path = generate_postmortem(state, nonexistent, tracker)

        assert path.parent == tmp_path


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestPostmortemPropertyTests:
    """Property-based tests for post-mortem generation."""

    @settings(max_examples=10)
    @given(
        halt_reason=st.sampled_from(
            ["attempts", "time", "tokens"]
        ),
        attempt_count=st.integers(min_value=1, max_value=20),
        task_group=st.integers(min_value=1, max_value=10),
    )
    def test_section_completeness(
        self,
        halt_reason: str,
        attempt_count: int,
        task_group: int,
    ) -> None:
        """TS-15-P3: Every post-mortem has all required sections.

        Property 3 from design.md.
        Validates: 15-REQ-3.2
        """
        import tempfile

        state = _make_halted_state(
            halt_reason=f"Max {halt_reason} exceeded",
            attempt_count=attempt_count,
            current_task_group=task_group,
        )
        tracker = _make_fake_tracker()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_postmortem(
                state, Path(tmpdir), tracker
            )
            content = path.read_text()

            for section in REQUIRED_SECTIONS:
                assert section in content, (
                    f"Missing section: {section}"
                )
