"""Rich-based console output for phase transitions and progress.

Provides the ``ConsoleLogger`` class that formats and displays
workflow progress, test results, token usage, and summaries.

Implements Requirements:
    15-REQ-4.1 (phase transitions), 15-REQ-4.2 (test results),
    15-REQ-4.3 (token usage), 15-REQ-4.4 (rich colors),
    15-REQ-4.5 (progress summary), 15-REQ-4.E1 (non-TTY fallback).
"""

from __future__ import annotations

import sys
from typing import IO, Any

from rich.console import Console


class ConsoleLogger:
    """Rich-based console logger for workflow progress.

    Uses ``rich.console.Console`` for formatted output with colors:
    green for pass, red for fail, yellow for warnings, blue for
    phase transitions.

    Parameters
    ----------
    force_terminal:
        If True, force ANSI color output even when the output is not a
        TTY. If False, disable ANSI codes. If None, auto-detect.
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
        target = file if file is not None else sys.stderr
        self._console = Console(
            file=target,
            force_terminal=force_terminal,
            # When force_terminal is explicitly False, we also need to
            # suppress color markup. Rich respects the no_color flag.
            no_color=(force_terminal is False),
        )

    def log_transition(
        self,
        phase: str,
        task_group: int,
        attempt: int,
        max_attempts: int,
    ) -> None:
        """Display current phase name and progress.

        Format: ``[task_group] phase (attempt N/max)``

        Parameters
        ----------
        phase:
            The current workflow phase name (e.g. "implement", "verify").
        task_group:
            The current task group number.
        attempt:
            The current attempt number within this task group.
        max_attempts:
            The maximum allowed attempts.
        """
        self._console.print(
            f"[bold blue]▸[/bold blue] "
            f"[{task_group}] "
            f"[bold blue]{phase}[/bold blue] "
            f"(attempt {attempt}/{max_attempts})"
        )

    def log_test_result(self, result: Any) -> None:
        """Display test pass/fail counts and command.

        Parameters
        ----------
        result:
            A ``VerificationResult`` with ``passed``, ``exit_code``,
            ``stdout``, ``command``, and ``elapsed_seconds`` attributes.
        """
        passed = getattr(result, "passed", False)
        command = getattr(result, "command", "")
        stdout = getattr(result, "stdout", "")
        elapsed = getattr(result, "elapsed_seconds", 0.0)

        if passed:
            icon = "✓"
            style = "bold green"
            status = "PASS"
        else:
            icon = "✗"
            style = "bold red"
            status = "FAIL"

        self._console.print(
            f"[{style}]{icon} {status}[/{style}] "
            f"{command} ({elapsed:.1f}s)"
        )
        if stdout and stdout.strip():
            # Print a condensed version of the test output
            lines = stdout.strip().splitlines()
            # Show last few lines which typically have the summary
            summary_lines = lines[-3:] if len(lines) > 3 else lines
            for line in summary_lines:
                self._console.print(f"  {line}")

    def log_token_usage(
        self,
        tracker: Any,
        elapsed: float,
    ) -> None:
        """Display running token usage and elapsed time.

        Parameters
        ----------
        tracker:
            A ``TokenTracker`` (or compatible) with ``input_tokens``,
            ``output_tokens``, and ``total_tokens`` attributes.
        elapsed:
            Total elapsed time in seconds since the run started.
        """
        input_t = getattr(tracker, "input_tokens", 0)
        output_t = getattr(tracker, "output_tokens", 0)
        total_t = getattr(tracker, "total_tokens", 0)

        self._console.print(
            f"[yellow]⟡ tokens:[/yellow] "
            f"{input_t:,} in / {output_t:,} out / {total_t:,} total "
            f"| elapsed {elapsed:.1f}s"
        )

    def print_summary(self, summary: str) -> None:
        """Print a condensed run summary.

        Parameters
        ----------
        summary:
            Pre-formatted summary string to display.
        """
        self._console.rule("[bold]Run Summary[/bold]")
        self._console.print(summary)
        self._console.rule()
