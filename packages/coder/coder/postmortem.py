"""Post-mortem document generation.

Generates a ``_postmortem.md`` markdown file from the final graph state
when execution is halted by the circuit breaker.

Implements Requirements:
    15-REQ-3.1 (file location), 15-REQ-3.2 (sections),
    15-REQ-3.3 (terminal node), 15-REQ-3.4 (I/O error handling),
    15-REQ-3.E1 (fallback to cwd).

Note: Stub module for import compatibility (task group 1).
      Full implementation in task group 4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_postmortem(
    state: dict[str, Any],
    worktree: Path,
    tracker: Any,
) -> Path:
    """Generate ``_postmortem.md`` and return its path.

    Stub — raises NotImplementedError until task group 4.
    """
    raise NotImplementedError("generate_postmortem not yet implemented")


def generate_postmortem_node(state: dict[str, Any]) -> dict[str, Any]:
    """Terminal graph node that generates the post-mortem.

    Reads the final graph state, generates the post-mortem file,
    and returns the state unchanged.

    Stub — raises NotImplementedError until task group 4.
    """
    raise NotImplementedError(
        "generate_postmortem_node not yet implemented"
    )


def perform_graceful_shutdown(
    state: dict[str, Any],
    worktree: Path,
    tracker: Any,
) -> None:
    """Graceful shutdown: persist state and generate post-mortem.

    Stub — raises NotImplementedError until task group 4.
    """
    raise NotImplementedError(
        "perform_graceful_shutdown not yet implemented"
    )
