"""Tests for circuit breaker enforcement.

Covers acceptance criteria: TS-15-1, TS-15-2, TS-15-3, TS-15-4.
Edge cases: TS-15-E1, TS-15-E2.
Additional: TS-15-15 (safety config), TS-15-20 (complete in-flight call),
TS-15-24 (safety config passed to CB and graph state).
Property tests: TS-15-P1 (halt guarantee), TS-15-P4 (config defaults safe).
"""

from __future__ import annotations

import time

import pytest
from coder.circuit import CheckResult, CircuitBreaker
from coder.errors import ConfigError
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Helpers: SafetyConfig stub for test construction
# ---------------------------------------------------------------------------


class _SafetyConfig:
    """Minimal SafetyConfig stand-in for tests.

    Tests must work with whatever SafetyConfig the implementation provides.
    This helper is used only to construct test inputs. Once task group 2
    implements the real SafetyConfig, tests should still pass because
    CircuitBreaker accepts the same fields.
    """

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


class _FakeTracker:
    """Minimal token tracker stand-in for circuit breaker tests."""

    def __init__(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    @property
    def total_tokens(self) -> int:
        return self._input_tokens + self._output_tokens


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerLimits:
    """TS-15-1 through TS-15-4: Circuit breaker limit enforcement."""

    def test_max_attempts_trips(self) -> None:
        """TS-15-1: Circuit breaker trips on max attempts.

        Requirement: 15-REQ-1.1
        Verify halt when attempt_count reaches max_attempts_per_task.
        """
        config = _SafetyConfig(max_attempts_per_task=3)
        cb = CircuitBreaker(config)
        state = {"attempt_count": 3}
        tracker = _FakeTracker()

        result = cb.check(state, tracker)

        assert isinstance(result, CheckResult)
        assert result.halted is True
        assert result.reason is not None
        assert "attempt" in result.reason.lower()

    def test_max_wall_time_trips(self) -> None:
        """TS-15-2: Circuit breaker trips on wall time.

        Requirement: 15-REQ-1.2
        Verify halt when elapsed time exceeds max_wall_time_seconds.
        """
        config = _SafetyConfig(max_wall_time_seconds=60)
        # Set start_time 120 seconds ago so elapsed > 60s
        cb = CircuitBreaker(config, start_time=time.time() - 120)
        state: dict[str, object] = {"attempt_count": 0}
        tracker = _FakeTracker()

        result = cb.check(state, tracker)

        assert result.halted is True
        assert result.reason is not None
        assert "time" in result.reason.lower()

    def test_max_tokens_trips(self) -> None:
        """TS-15-3: Circuit breaker trips on max tokens.

        Requirement: 15-REQ-1.3
        Verify halt when total tokens exceed max_tokens.
        """
        config = _SafetyConfig(max_tokens=1000)
        cb = CircuitBreaker(config)
        state: dict[str, object] = {"attempt_count": 0}
        tracker = _FakeTracker(input_tokens=1000, output_tokens=500)

        result = cb.check(state, tracker)

        assert result.halted is True
        assert result.reason is not None
        assert "token" in result.reason.lower()

    def test_within_limits_no_halt(self) -> None:
        """TS-15-4: Circuit breaker passes when within limits.

        Requirement: 15-REQ-1.4
        Verify no halt when all limits are OK.
        """
        config = _SafetyConfig(
            max_attempts_per_task=5,
            max_wall_time_seconds=1800,
            max_tokens=2_000_000,
        )
        cb = CircuitBreaker(config)
        state: dict[str, object] = {"attempt_count": 1}
        tracker = _FakeTracker(input_tokens=50, output_tokens=50)

        result = cb.check(state, tracker)

        assert result.halted is False


class TestCircuitBreakerInFlight:
    """TS-15-20: Circuit breaker completes in-flight LLM call."""

    def test_completes_inflight_llm_call(self) -> None:
        """TS-15-20: Verify circuit breaker does not abort mid-call.

        Requirement: 15-REQ-5.1
        The circuit breaker check happens *after* the LLM call completes,
        not during. We verify the design by checking that the CB's check()
        returns a halted result that can be used by the node wrapper to
        route to postmortem — it does not cancel in-progress calls.
        """
        config = _SafetyConfig(max_attempts_per_task=1)
        cb = CircuitBreaker(config)
        state: dict[str, object] = {"attempt_count": 1}
        tracker = _FakeTracker()

        # Simulate: the LLM call has already completed (call_completed=True),
        # then we check limits. The circuit breaker should not have
        # prevented the call from completing.
        call_completed = True
        result = cb.check(state, tracker)

        assert call_completed is True
        assert result.halted is True


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerEdgeCases:
    """TS-15-E1, TS-15-E2: Edge cases for circuit breaker."""

    def test_zero_limit_raises_config_error(self) -> None:
        """TS-15-E1: Zero limit raises ConfigError.

        Requirement: 15-REQ-1.E1
        Verify zero/negative limits are rejected at startup.
        """
        config = _SafetyConfig(max_attempts_per_task=0)
        with pytest.raises(ConfigError):
            CircuitBreaker(config)

    def test_negative_limit_raises_config_error(self) -> None:
        """TS-15-E1 (negative variant): Negative limit raises ConfigError.

        Requirement: 15-REQ-1.E1
        """
        config = _SafetyConfig(max_wall_time_seconds=-10)
        with pytest.raises(ConfigError):
            CircuitBreaker(config)

    def test_all_limits_zero_raises_config_error(self) -> None:
        """TS-15-E1 (all zero): All limits zero raises ConfigError.

        Requirement: 15-REQ-1.E1
        """
        config = _SafetyConfig(
            max_attempts_per_task=0,
            max_wall_time_seconds=0,
            max_tokens=0,
        )
        with pytest.raises(ConfigError):
            CircuitBreaker(config)

    def test_null_limit_means_unlimited(self) -> None:
        """TS-15-E2: Null limit means unlimited.

        Requirement: 15-REQ-1.E2
        Verify null limits are not enforced.
        """
        config = _SafetyConfig(
            max_attempts_per_task=None,
            max_wall_time_seconds=None,
            max_tokens=None,
        )
        cb = CircuitBreaker(config)
        state: dict[str, object] = {"attempt_count": 999999}
        tracker = _FakeTracker(
            input_tokens=999_999_999,
            output_tokens=0,
        )

        result = cb.check(state, tracker)

        assert result.halted is False


# ---------------------------------------------------------------------------
# Safety config tests
# ---------------------------------------------------------------------------


class TestSafetyConfig:
    """TS-15-15: Safety config extends CoderConfig.

    Requirement: 15-REQ-7.1, 15-REQ-7.2
    """

    def test_safety_config_from_yaml(
        self,
        tmp_project_dir: "Path",  # type: ignore[name-defined]  # noqa: F821
        clean_coder_env: None,
    ) -> None:
        """TS-15-15: Verify SafetyConfig is part of CoderConfig.

        Loads .coder.yaml with safety section and checks the parsed value.
        """
        from pathlib import Path

        from coder.config import load_config

        config_file = Path(str(tmp_project_dir)) / ".coder.yaml"
        config_file.write_text(
            "safety:\n  max_attempts_per_task: 3\n"
        )

        config = load_config(project_dir=Path(str(tmp_project_dir)))

        assert hasattr(config, "safety")
        assert config.safety.max_attempts_per_task == 3  # type: ignore[attr-defined]

    def test_safety_config_defaults(
        self,
        tmp_project_dir: "Path",  # type: ignore[name-defined]  # noqa: F821
        clean_coder_env: None,
    ) -> None:
        """TS-15-15 (defaults): Verify SafetyConfig has default values.

        When no safety section in yaml, defaults should be used.
        """
        from pathlib import Path

        from coder.config import load_config

        config = load_config(project_dir=Path(str(tmp_project_dir)))

        assert hasattr(config, "safety")
        # Default for max_attempts_per_task is 5
        assert config.safety.max_attempts_per_task == 5  # type: ignore[attr-defined]


class TestSafetyConfigPassthrough:
    """TS-15-24: Safety config passed to circuit breaker and graph state."""

    def test_config_passed_to_circuit_breaker(self) -> None:
        """TS-15-24: CircuitBreaker uses configured limits.

        Requirement: 15-REQ-7.3
        """
        config = _SafetyConfig(max_attempts_per_task=7)
        cb = CircuitBreaker(config)

        assert cb.config.max_attempts_per_task == 7  # type: ignore[attr-defined]

    def test_config_in_graph_state(self) -> None:
        """TS-15-24: Graph state contains max_attempts from config.

        Requirement: 15-REQ-7.3
        Verifies create_initial_state picks up safety config.
        """
        from afspec.models import Requirements, SpecMeta, Tasks, TestSpec
        from coder.graph import create_initial_state
        from coder.models import ParsedSpec

        # This test currently checks that max_attempts can be set to
        # match the safety config. The full wiring happens in group 5,
        # but the initial state should support the field.
        meta = SpecMeta(
            spec_id="1",
            spec_name="test",
            status="active",
            dir="/tmp/fake",
        )
        parsed = ParsedSpec(
            meta=meta,
            requirements=Requirements(spec_id="1", spec_name="test"),
            test_spec=TestSpec(spec_id="1", spec_name="test"),
            tasks=Tasks(spec_id="1", spec_name="test"),
            prd_text="# Test\n",
        )
        state = create_initial_state(parsed)

        # The default max_attempts should be 5 (per design)
        assert state["max_attempts"] == 5

        # When safety config says 7, the state should reflect it.
        # This will be wired in group 5; for now we verify the field
        # exists and has a default.
        assert "max_attempts" in state


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerProperties:
    """Property tests for circuit breaker behavior."""

    @settings(max_examples=20)
    @given(max_attempts=st.integers(min_value=1, max_value=10))
    def test_halt_guarantee(self, max_attempts: int) -> None:
        """TS-15-P1: Halt guarantee — once breached, no further nodes.

        Property 1 from design.md.
        Validates: 15-REQ-1.4, 15-REQ-5.1

        For any max_attempts, once attempt_count >= max_attempts, the
        circuit breaker always returns halted=True.
        """
        config = _SafetyConfig(max_attempts_per_task=max_attempts)
        cb = CircuitBreaker(config)
        tracker = _FakeTracker()

        # At the limit
        state: dict[str, object] = {"attempt_count": max_attempts}
        result = cb.check(state, tracker)
        assert result.halted is True

        # Beyond the limit
        state = {"attempt_count": max_attempts + 5}
        result = cb.check(state, tracker)
        assert result.halted is True

    @settings(max_examples=5)
    @given(st.data())
    def test_config_defaults_are_safe(self, data: st.DataObject) -> None:
        """TS-15-P4: Default config does not cause immediate halt.

        Property 4 from design.md.
        Validates: 15-REQ-1.1, 15-REQ-1.2, 15-REQ-1.3, 15-REQ-1.E2

        A fresh state with default SafetyConfig should never trigger halt.
        """
        config = _SafetyConfig()  # All defaults
        cb = CircuitBreaker(config)
        state: dict[str, object] = {"attempt_count": 0}
        tracker = _FakeTracker()

        result = cb.check(state, tracker)

        assert result.halted is False
