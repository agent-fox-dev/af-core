"""Rich-based console output for phase transitions and progress.

Provides the ``ConsoleLogger`` class that formats and displays
workflow progress, test results, token usage, and summaries.

Implements Requirements:
    15-REQ-4.1 (phase transitions), 15-REQ-4.2 (test results),
    15-REQ-4.3 (token usage), 15-REQ-4.4 (rich colors),
    15-REQ-4.5 (progress summary), 15-REQ-4.E1 (non-TTY fallback).

Note: Stub module for import compatibility (task group 1).
      Full implementation in task group 3.
"""

from __future__ import annotations

from typing import IO, Any


class ConsoleLogger:
    """Rich-based console logger for workflow progress.

    Stub — raises NotImplementedError until task group 3.

    Parameters
    ----------
    force_terminal:
        If True, force ANSI color output even when the output is not a TTY.
        If False, disable ANSI codes. If None, auto-detect.
    file:
        Optional file-like object to write output to (default: stderr).
        Useful for testing — pass an ``io.StringIO`` to capture output.
    """

    def __init__(
        self,
        *,
        force_terminal: bool | None = None,
        file: IO[str] | None = None,
    ) -> None:
        raise NotImplementedError("ConsoleLogger not yet implemented")

    def log_transition(
        self,
        phase: str,
        task_group: int,
        attempt: int,
        max_attempts: int,
    ) -> None:
        """Display current phase name and progress."""
        raise NotImplementedError

    def log_test_result(self, result: Any) -> None:
        """Display test pass/fail counts."""
        raise NotImplementedError

    def log_token_usage(
        self,
        tracker: Any,
        elapsed: float,
    ) -> None:
        """Display running token usage and elapsed time."""
        raise NotImplementedError

    def print_summary(self, summary: str) -> None:
        """Print a condensed run summary."""
        raise NotImplementedError
