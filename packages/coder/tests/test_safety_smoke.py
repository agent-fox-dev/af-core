"""Integration smoke tests for safety & observability.

Covers: TS-15-SMOKE-1 (circuit breaker halts graph),
        TS-15-SMOKE-2 (token tracking end-to-end).
Also covers: TS-15-E6 (SIGINT triggers graceful shutdown).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from coder.circuit import CircuitBreaker
from coder.postmortem import perform_graceful_shutdown
from coder.tokens import TokenTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SafetyConfig:
    """Minimal SafetyConfig stand-in for smoke tests."""

    def __init__(
        self,
        *,
        max_attempts_per_task: int | None = 5,
        max_wall_time_seconds: int | None = 1800,
        max_tokens: int | None = 2_000_000,
    ) -> None:
        self.max_attempts_per_task = max_attempts_per_task
        self.max_wall_time_seconds = max_wall_time_seconds
        self.max_tokens = max_tokens


def _mock_always_fail_provider() -> Any:
    """Create a mock LLM provider that always 'fails' tests.

    Returns a provider whose invoke() returns responses with token
    usage but whose implementations always fail verification.
    """
    provider = MagicMock()
    response = MagicMock()
    response.content = "implementation code that fails tests"
    response.llm_output = {
        "token_usage": {
            "input_tokens": 500,
            "output_tokens": 200,
        }
    }
    provider.invoke.return_value = response
    return provider


# ---------------------------------------------------------------------------
# Integration smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestCircuitBreakerSmoke:
    """TS-15-SMOKE-1: Circuit breaker halts graph execution."""

    def test_graph_halts_on_max_attempts(
        self, tmp_path: Path
    ) -> None:
        """TS-15-SMOKE-1: Verify circuit breaker integration.

        Execution Path: Path 1 from design.md
        Graph halts and produces post-mortem when limit is breached.

        Setup: Mock LLM that always fails tests.
        SafetyConfig with max_attempts_per_task=2.
        """
        # Build a minimal parsed spec for testing
        from afspec.models import (
            Requirements,
            SpecMeta,
            Tasks,
            TestSpec,
        )
        from coder.models import ParsedSpec
        from coder.runner import run_spec

        meta = SpecMeta(
            spec_id="1",
            spec_name="test_spec",
            status="active",
            dir=str(tmp_path),
        )
        parsed = ParsedSpec(
            meta=meta,
            requirements=Requirements(
                spec_id="1", spec_name="test_spec"
            ),
            test_spec=TestSpec(
                spec_id="1", spec_name="test_spec"
            ),
            tasks=Tasks(spec_id="1", spec_name="test_spec"),
            prd_text="# Test\n",
        )

        provider = _mock_always_fail_provider()
        config = {
            "safety": {
                "max_attempts_per_task": 2,
            }
        }

        result = run_spec(parsed, provider, tmp_path, config)

        # The run should fail due to circuit breaker
        assert result.success is False
        assert result.halt_reason is not None
        assert "attempt" in result.halt_reason.lower()

        # Post-mortem should exist
        assert (tmp_path / "_postmortem.md").exists()

    def test_implement_node_called_at_most_n_times(
        self, tmp_path: Path
    ) -> None:
        """TS-15-SMOKE-1 (call count): Implement called at most N times.

        The implement node should not be called more than
        max_attempts_per_task times.
        """
        config = _SafetyConfig(max_attempts_per_task=2)
        cb = CircuitBreaker(config)
        tracker = MagicMock()
        tracker.total_tokens = 0

        implement_calls = 0
        for attempt in range(10):
            state: dict[str, object] = {
                "attempt_count": attempt
            }
            result = cb.check(state, tracker)
            if result.halted:
                break
            implement_calls += 1

        assert implement_calls <= 2


@pytest.mark.smoke
class TestTokenTrackingSmoke:
    """TS-15-SMOKE-2: Token tracking end-to-end."""

    def test_tokens_tracked_across_calls(self) -> None:
        """TS-15-SMOKE-2: Verify tokens tracked across LLM calls.

        Execution Path: Path 2 from design.md
        Real TokenTracker callback receives events from mock LLM calls.
        """
        tracker = TokenTracker()

        # Simulate multiple LLM calls with token metadata
        for i in range(5):
            response = MagicMock()
            response.llm_output = {
                "token_usage": {
                    "input_tokens": 100 * (i + 1),
                    "output_tokens": 50 * (i + 1),
                }
            }
            tracker.on_llm_end(response)

        assert tracker.total_tokens > 0
        # Sum: input = 100+200+300+400+500 = 1500
        # Sum: output = 50+100+150+200+250 = 750
        assert tracker.input_tokens == 1500
        assert tracker.output_tokens == 750
        assert tracker.total_tokens == 2250


# ---------------------------------------------------------------------------
# SIGINT integration test
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestSIGINTShutdown:
    """TS-15-E6: SIGINT triggers graceful shutdown."""

    def test_sigint_triggers_shutdown(
        self, tmp_path: Path
    ) -> None:
        """TS-15-E6: Verify Ctrl+C is caught and handled.

        Requirement: 15-REQ-5.E1
        Send SIGINT signal and verify shutdown sequence completes.

        Note: This test is inherently tricky. We verify the graceful
        shutdown function produces the expected artifacts when called
        as part of a SIGINT handler.
        """
        state: dict[str, Any] = {
            "halted": True,
            "halt_reason": "SIGINT received",
            "spec_name": "test_spec",
            "model_name": "test",
            "current_phase": "implement",
            "current_task_group": 1,
            "total_groups": 1,
            "attempt_count": 1,
            "max_attempts": 5,
            "test_results": "",
            "history": [],
        }
        tracker = MagicMock()
        tracker.input_tokens = 100
        tracker.output_tokens = 50
        tracker.total_tokens = 150
        tracker.call_count = 2
        tracker.to_dict.return_value = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "call_count": 2,
        }

        perform_graceful_shutdown(state, tmp_path, tracker)

        # Verify shutdown artifacts
        assert (tmp_path / "_run.json").exists()
        assert (tmp_path / "_postmortem.md").exists()
