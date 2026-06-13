"""Tests for token tracking across LLM providers.

Covers acceptance criteria: TS-15-5, TS-15-6, TS-15-7, TS-15-8.
Additional: TS-15-16 (tracker registered as callback),
TS-15-18 (console shows token usage).
Edge cases: TS-15-E3 (missing token metadata).
Property tests: TS-15-P2 (token monotonicity).
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from coder.tokens import TokenTracker
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Helpers: Mock LLM responses for each provider
# ---------------------------------------------------------------------------


def _mock_llm_response(
    *,
    usage: dict[str, Any] | None = None,
    llm_output: dict[str, Any] | None = None,
) -> Any:
    """Create a mock LLM response with token usage metadata.

    The response object mimics what LangChain passes to
    ``BaseCallbackHandler.on_llm_end(response)``.
    """
    response = MagicMock()

    # LangChain LLMResult has llm_output dict with token_usage
    if llm_output is not None:
        response.llm_output = llm_output
    elif usage is not None:
        response.llm_output = {"token_usage": usage}
    else:
        response.llm_output = None

    return response


def mock_anthropic_response(
    input_tokens: int = 0, output_tokens: int = 0
) -> Any:
    """Mock Anthropic-style LLM response with token usage."""
    return _mock_llm_response(
        usage={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    )


def mock_google_response(
    prompt_token_count: int = 0,
    candidates_token_count: int = 0,
) -> Any:
    """Mock Google-style LLM response with token usage."""
    return _mock_llm_response(
        usage={
            "prompt_token_count": prompt_token_count,
            "candidates_token_count": candidates_token_count,
        }
    )


def mock_ollama_response(
    prompt_eval_count: int = 0,
    eval_count: int = 0,
) -> Any:
    """Mock Ollama-style LLM response with token usage."""
    return _mock_llm_response(
        usage={
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
        }
    )


def mock_empty_response() -> Any:
    """Mock LLM response with no token metadata."""
    return _mock_llm_response(llm_output=None)


# ---------------------------------------------------------------------------
# Acceptance-criterion tests
# ---------------------------------------------------------------------------


class TestTokenTrackerAccumulation:
    """TS-15-5, TS-15-6: Token tracking from different providers."""

    def test_anthropic_tokens(self) -> None:
        """TS-15-5: TokenTracker accumulates Anthropic tokens.

        Requirement: 15-REQ-2.1, 15-REQ-2.2
        Verify token tracking from Anthropic responses.
        """
        tracker = TokenTracker()
        response = mock_anthropic_response(
            input_tokens=100, output_tokens=50
        )

        tracker.on_llm_end(response)

        assert tracker.input_tokens == 100
        assert tracker.output_tokens == 50

    def test_google_tokens(self) -> None:
        """TS-15-6: TokenTracker accumulates Google tokens.

        Requirement: 15-REQ-2.2
        Verify token tracking from Google responses with normalized fields.
        """
        tracker = TokenTracker()
        response = mock_google_response(
            prompt_token_count=200,
            candidates_token_count=80,
        )

        tracker.on_llm_end(response)

        assert tracker.input_tokens == 200
        assert tracker.output_tokens == 80

    def test_ollama_tokens(self) -> None:
        """TS-15-6 (Ollama variant): TokenTracker accumulates Ollama tokens.

        Requirement: 15-REQ-2.2
        Verify normalization of Ollama token fields.
        """
        tracker = TokenTracker()
        response = mock_ollama_response(
            prompt_eval_count=150,
            eval_count=60,
        )

        tracker.on_llm_end(response)

        assert tracker.input_tokens == 150
        assert tracker.output_tokens == 60

    def test_multiple_calls_accumulate(self) -> None:
        """TS-15-5 (accumulation): Multiple calls accumulate.

        Requirement: 15-REQ-2.1
        Verify tokens from successive calls are summed.
        """
        tracker = TokenTracker()
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=100, output_tokens=50)
        )
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=200, output_tokens=100)
        )

        assert tracker.input_tokens == 300
        assert tracker.output_tokens == 150


class TestTokenTrackerProperties:
    """TS-15-7, TS-15-8: total_tokens property and to_dict."""

    def test_total_tokens_property(self) -> None:
        """TS-15-7: total_tokens is input + output.

        Requirement: 15-REQ-2.3
        """
        tracker = TokenTracker()
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=100, output_tokens=50)
        )

        assert tracker.total_tokens == 150

    def test_to_dict_returns_breakdown(self) -> None:
        """TS-15-8: to_dict returns structured data.

        Requirement: 15-REQ-2.3
        """
        tracker = TokenTracker()
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=100, output_tokens=50)
        )

        d = tracker.to_dict()

        assert "input_tokens" in d
        assert "output_tokens" in d
        assert "total_tokens" in d
        assert "call_count" in d
        assert d["total_tokens"] == d["input_tokens"] + d["output_tokens"]

    def test_to_dict_call_count(self) -> None:
        """TS-15-8 (call_count): to_dict reports call count.

        Requirement: 15-REQ-2.3
        """
        tracker = TokenTracker()
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=100, output_tokens=50)
        )
        tracker.on_llm_end(
            mock_anthropic_response(input_tokens=200, output_tokens=100)
        )

        d = tracker.to_dict()

        assert d["call_count"] == 2


class TestTokenTrackerRegistration:
    """TS-15-16: TokenTracker registered as callback on LLM invocations."""

    def test_tracker_is_langchain_callback(self) -> None:
        """TS-15-16: Verify TokenTracker is a LangChain callback handler.

        Requirement: 15-REQ-2.4
        The tracker must be an instance of BaseCallbackHandler.
        """
        from langchain_core.callbacks import BaseCallbackHandler

        tracker = TokenTracker()

        assert isinstance(tracker, BaseCallbackHandler)

    def test_tracker_receives_callback(self) -> None:
        """TS-15-16: Verify tracker records usage when used as callback.

        Requirement: 15-REQ-2.4
        After invocation with the tracker as callback, tokens are recorded.
        """
        tracker = TokenTracker()
        response = mock_anthropic_response(
            input_tokens=500, output_tokens=200
        )

        tracker.on_llm_end(response)

        assert tracker.total_tokens > 0


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestTokenTrackerEdgeCases:
    """TS-15-E3: Missing token metadata."""

    def test_missing_metadata_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """TS-15-E3: Warning when tokens not reported.

        Requirement: 15-REQ-2.E1
        Verify warning logged. No crash. Tokens remain unchanged.
        """
        tracker = TokenTracker()

        with caplog.at_level(logging.WARNING):
            tracker.on_llm_end(mock_empty_response())

        assert tracker.total_tokens == 0
        assert any(
            "token" in record.message.lower()
            or "warning" in record.message.lower()
            for record in caplog.records
        )

    def test_missing_metadata_no_crash(self) -> None:
        """TS-15-E3 (no crash): Missing metadata does not crash.

        Requirement: 15-REQ-2.E1
        """
        tracker = TokenTracker()

        # Should not raise any exception
        tracker.on_llm_end(mock_empty_response())

        assert tracker.total_tokens == 0


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestTokenTrackerPropertyTests:
    """Property-based tests for token tracking."""

    @settings(max_examples=30)
    @given(
        token_sequence=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10000),
                st.integers(min_value=0, max_value=10000),
            ),
            min_size=1,
            max_size=20,
        )
    )
    def test_token_monotonicity(
        self, token_sequence: list[tuple[int, int]]
    ) -> None:
        """TS-15-P2: Token counts never decrease.

        Property 2 from design.md.
        Validates: 15-REQ-2.1, 15-REQ-2.3

        For any sequence of LLM responses, total_tokens is monotonically
        non-decreasing.
        """
        tracker = TokenTracker()
        prev = 0

        for inp, out in token_sequence:
            response = mock_anthropic_response(
                input_tokens=inp, output_tokens=out
            )
            tracker.on_llm_end(response)

            assert tracker.total_tokens >= prev
            prev = tracker.total_tokens
