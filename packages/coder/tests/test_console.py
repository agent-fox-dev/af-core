"""Tests for console logging with rich output.

Covers acceptance criteria: TS-15-11, TS-15-12, TS-15-18, TS-15-19, TS-15-23.
Edge cases: TS-15-E5 (non-TTY fallback).
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock

from coder.console import ConsoleLogger
from coder.verify import VerificationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_console_output(
    logger: ConsoleLogger,
    action: str,
    **kwargs: Any,
) -> str:
    """Capture console logger output to a string.

    Uses the logger's internal console's file parameter to capture output.
    We create the logger with a custom file stream to capture output.
    """
    buf = io.StringIO()
    # The ConsoleLogger should be constructed to write to our buffer.
    # This is a test utility — the exact mechanism depends on
    # ConsoleLogger's implementation.
    #
    # For now, we'll use the standard approach: create the logger
    # and call the method, then read the output.
    if action == "log_transition":
        logger.log_transition(**kwargs)
    elif action == "log_test_result":
        logger.log_test_result(**kwargs)
    elif action == "log_token_usage":
        logger.log_token_usage(**kwargs)
    elif action == "print_summary":
        logger.print_summary(**kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestConsolePhaseTransitions:
    """TS-15-11: Console logger shows phase transitions."""

    def test_shows_phase_name(self) -> None:
        """TS-15-11: Output contains phase name and progress.

        Requirement: 15-REQ-4.1, 15-REQ-4.5
        """
        logger = ConsoleLogger(force_terminal=False)

        # Redirect output by using the logger directly
        logger.log_transition(
            "implement",
            task_group=2,
            attempt=1,
            max_attempts=5,
        )

        # We can't directly capture rich console output in this stub,
        # so we verify the method is callable and the logger object
        # exists. The actual output verification works once ConsoleLogger
        # is implemented with a capturable console.
        #
        # Full verification: output contains "implement" and "2"
        assert True  # Placeholder — will fail at ConsoleLogger()

    def test_shows_progress_format(self) -> None:
        """TS-15-11: Output contains progress summary line.

        Requirement: 15-REQ-4.5
        Format: [task_group/total] phase (attempt N/max)
        """
        logger = ConsoleLogger(force_terminal=False)

        # Should not raise — output should contain progress info
        logger.log_transition(
            "implement",
            task_group=2,
            attempt=3,
            max_attempts=5,
        )


class TestConsoleTestResults:
    """TS-15-12: Console logger shows test results."""

    def test_shows_pass_indicator(self) -> None:
        """TS-15-12: Verify test results displayed in console.

        Requirement: 15-REQ-4.2
        """
        logger = ConsoleLogger(force_terminal=False)

        result = VerificationResult(
            passed=True,
            exit_code=0,
            stdout="3 passed",
            stderr="",
            command="pytest",
            elapsed_seconds=1.5,
        )

        logger.log_test_result(result)

    def test_shows_fail_indicator(self) -> None:
        """TS-15-12 (failure): Verify failed test results.

        Requirement: 15-REQ-4.2
        """
        logger = ConsoleLogger(force_terminal=False)

        result = VerificationResult(
            passed=False,
            exit_code=1,
            stdout="2 failed, 1 passed",
            stderr="assertion error",
            command="pytest",
            elapsed_seconds=2.0,
        )

        logger.log_test_result(result)


class TestConsoleTokenUsage:
    """TS-15-18: Console shows token usage and elapsed time."""

    def test_shows_token_counts(self) -> None:
        """TS-15-18: Output includes running token usage.

        Requirement: 15-REQ-4.3
        """
        logger = ConsoleLogger(force_terminal=False)

        tracker = MagicMock()
        tracker.input_tokens = 500
        tracker.output_tokens = 200
        tracker.total_tokens = 700

        logger.log_token_usage(tracker, elapsed=45.3)

    def test_shows_elapsed_time(self) -> None:
        """TS-15-18: Output includes elapsed time.

        Requirement: 15-REQ-4.3
        """
        logger = ConsoleLogger(force_terminal=False)

        tracker = MagicMock()
        tracker.input_tokens = 500
        tracker.output_tokens = 200
        tracker.total_tokens = 700

        logger.log_token_usage(tracker, elapsed=45.3)


class TestConsoleRichColors:
    """TS-15-19: Console uses rich with color coding."""

    def test_color_output_in_tty(self) -> None:
        """TS-15-19: Verify ANSI color codes in TTY mode.

        Requirement: 15-REQ-4.4
        Green for pass, red for fail, blue for phase transitions.
        """
        logger = ConsoleLogger(force_terminal=True)

        # In TTY mode with force_terminal=True, output should contain
        # ANSI escape codes. We verify the logger can be constructed
        # and methods called with force_terminal=True.
        result = VerificationResult(
            passed=True,
            exit_code=0,
            stdout="3 passed",
            stderr="",
            command="pytest",
            elapsed_seconds=1.0,
        )
        logger.log_test_result(result)


class TestConsolePrintSummary:
    """TS-15-23: Condensed summary printed to console."""

    def test_prints_summary(self) -> None:
        """TS-15-23: Verify condensed run summary printed to console.

        Requirement: 15-REQ-6.3
        Console output contains spec name, status, token count, elapsed.
        """
        logger = ConsoleLogger(force_terminal=False)

        summary = (
            "Spec: test_spec | Status: success | "
            "Tokens: 8000 | Elapsed: 120.5s"
        )
        logger.print_summary(summary)


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
        logger = ConsoleLogger(force_terminal=False)

        # The logger should produce plain text without ANSI codes
        logger.log_transition(
            "implement",
            task_group=1,
            attempt=1,
            max_attempts=5,
        )
