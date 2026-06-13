"""Run summary document generation.

Generates a ``_run_summary.md`` markdown file after execution completes,
summarizing spec name, model, groups, tokens, time, and status.

Implements Requirements:
    15-REQ-6.1 (file location), 15-REQ-6.2 (required fields),
    15-REQ-6.3 (console output), 15-REQ-6.E1 (write failure fallback).

Note: Stub module for import compatibility (task group 1).
      Full implementation in task group 4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_run_summary(
    state: dict[str, Any],
    worktree: Path,
    tracker: Any,
) -> Path:
    """Generate ``_run_summary.md`` and return its path.

    Stub — raises NotImplementedError until task group 4.
    """
    raise NotImplementedError("write_run_summary not yet implemented")
