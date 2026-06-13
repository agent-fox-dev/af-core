"""Circuit breaker for the TDD execution engine.

Enforces limits on attempts, wall time, and token consumption to
prevent runaway agent loops.

Implements Requirements:
    15-REQ-1.1 (max attempts), 15-REQ-1.2 (max wall time),
    15-REQ-1.3 (max tokens), 15-REQ-1.4 (halt on breach),
    15-REQ-1.5 (configurable limits), 15-REQ-1.E1 (zero/negative),
    15-REQ-1.E2 (null unlimited).

Note: Stub module for import compatibility (task group 1).
      Full implementation in task group 2.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result of a circuit breaker limit check.

    Attributes:
        halted: Whether execution should be halted.
        reason: Descriptive reason for the halt, or None if not halted.
    """

    halted: bool
    reason: str | None = None


class CircuitBreaker:
    """Check attempt, time, and token limits against graph state.

    Stub — raises NotImplementedError until task group 2.
    """

    def __init__(self, config: object, start_time: float | None = None) -> None:
        raise NotImplementedError("CircuitBreaker not yet implemented")

    def check(self, state: dict[str, object], token_tracker: object) -> CheckResult:
        """Check all limits against current state."""
        raise NotImplementedError("CircuitBreaker.check not yet implemented")
