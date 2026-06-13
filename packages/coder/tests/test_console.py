"""Tests for console logging with rich output.

Covers acceptance criteria: TS-15-11, TS-15-12, TS-15-18, TS-15-19, TS-15-23.
Edge cases: TS-15-E5 (non-TTY fallback).
"""

from __future__ import annotations

import io

from coder.console import ConsoleLogger
from coder.verify import VerificationResult

# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestConsolePhaseTransitions:
    """TS-15-11: Console logger shows phase transitions."""

    def test_shows_phase_name(self) -> None:
        """TS-15-11: Output contains phase name and progress.

        Requirement: 15-REQ-4.1, 15-REQ-4.5
        Verify the phase name and task group number appear in output.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        logger.log_transition(
            "implement",
            task_group=2,
            attempt=1,
            max_attempts=5,
        )

        output = buf.getvalue()
        assert "implement" in output
        assert "2" in output

    def test_shows_progress_format(self) -> None:
        """TS-15-11: Output contains progress summary line.

        Requirement: 15-REQ-4.5
        Format: [task_group/total] phase (attempt N/max)
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        logger.log_transition(
            "implement",
            task_group=2,
            attempt=3,
            max_attempts=5,
        )

        output = buf.getvalue()
        # Progress should include attempt info
        assert "3" in output
        assert "5" in output


class TestConsoleTestResults:
    """TS-15-12: Console logger shows test results."""

    def test_shows_pass_indicator(self) -> None:
        """TS-15-12: Verify passing test results displayed in console.

        Requirement: 15-REQ-4.2
        Output should contain a pass indicator (e.g. 'pass' or a checkmark).
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        result = VerificationResult(
            passed=True,
            exit_code=0,
            stdout="3 passed",
            stderr="",
            command="pytest",
            elapsed_seconds=1.5,
        )

        logger.log_test_result(result)

        output = buf.getvalue().lower()
        assert "pass" in output or "✓" in output

    def test_shows_fail_indicator(self) -> None:
        """TS-15-12 (failure): Verify failed test results.

        Requirement: 15-REQ-4.2
        Output should contain a fail indicator.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        result = VerificationResult(
            passed=False,
            exit_code=1,
            stdout="2 failed, 1 passed",
            stderr="assertion error",
            command="pytest",
            elapsed_seconds=2.0,
        )

        logger.log_test_result(result)

        output = buf.getvalue().lower()
        assert "fail" in output or "✗" in output


class TestConsoleTokenUsage:
    """TS-15-18: Console shows token usage and elapsed time."""

    def test_shows_token_counts(self) -> None:
        """TS-15-18: Output includes running token usage.

        Requirement: 15-REQ-4.3
        Verify that token counts appear in the output.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        from unittest.mock import MagicMock

        tracker = MagicMock()
        tracker.input_tokens = 500
        tracker.output_tokens = 200
        tracker.total_tokens = 700

        logger.log_token_usage(tracker, elapsed=45.3)

        output = buf.getvalue()
        # Should contain either individual counts or total
        assert "500" in output or "700" in output

    def test_shows_elapsed_time(self) -> None:
        """TS-15-18: Output includes elapsed time.

        Requirement: 15-REQ-4.3
        Verify that elapsed time appears in the output.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        from unittest.mock import MagicMock

        tracker = MagicMock()
        tracker.input_tokens = 500
        tracker.output_tokens = 200
        tracker.total_tokens = 700

        logger.log_token_usage(tracker, elapsed=45.3)

        output = buf.getvalue()
        assert "45" in output


class TestConsoleRichColors:
    """TS-15-19: Console uses rich with color coding."""

    def test_color_output_in_tty(self) -> None:
        """TS-15-19: Verify ANSI color codes in TTY mode.

        Requirement: 15-REQ-4.4
        Green for pass, red for fail, blue for phase transitions.
        When force_terminal=True, output should contain ANSI escape codes.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=True, file=buf)

        result = VerificationResult(
            passed=True,
            exit_code=0,
            stdout="3 passed",
            stderr="",
            command="pytest",
            elapsed_seconds=1.0,
        )
        logger.log_test_result(result)

        output = buf.getvalue()
        # ANSI escape codes start with ESC[
        assert "\033[" in output


class TestConsolePrintSummary:
    """TS-15-23: Condensed summary printed to console."""

    def test_prints_summary(self) -> None:
        """TS-15-23: Verify condensed run summary printed to console.

        Requirement: 15-REQ-6.3
        Console output contains spec name, status, token count, elapsed.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        summary = (
            "Spec: test_spec | Status: success | "
            "Tokens: 8000 | Elapsed: 120.5s"
        )
        logger.print_summary(summary)

        output = buf.getvalue()
        assert "success" in output.lower() or "test_spec" in output
        assert "token" in output.lower() or "8000" in output


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestConsoleEdgeCases:
    """TS-15-E5: Non-TTY fallback."""

    def test_no_ansi_in_non_tty(self) -> None:
        """TS-15-E5: Verify color-free output in non-TTY mode.

        Requirement: 15-REQ-4.E1
        When force_terminal=False (non-TTY), output should not contain
        ANSI escape codes.
        """
        buf = io.StringIO()
        logger = ConsoleLogger(force_terminal=False, file=buf)

        logger.log_transition(
            "implement",
            task_group=1,
            attempt=1,
            max_attempts=5,
        )

        output = buf.getvalue()
        assert "\033[" not in output
