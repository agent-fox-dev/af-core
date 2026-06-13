"""Token tracking callback handler for LLM calls.

Accumulates token counts across providers (Anthropic, Google, Ollama)
using LangChain's BaseCallbackHandler.

Implements Requirements:
    15-REQ-2.1 (accumulate tokens), 15-REQ-2.2 (normalize providers),
    15-REQ-2.3 (total_tokens, to_dict), 15-REQ-2.4 (callback registration),
    15-REQ-2.E1 (missing metadata).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider-specific field mappings
# ---------------------------------------------------------------------------
# Each provider reports token usage under different field names.
# We normalize them all to (input_tokens, output_tokens).

_INPUT_FIELD_NAMES = (
    "input_tokens",        # Anthropic
    "prompt_token_count",  # Google
    "prompt_eval_count",   # Ollama
    "prompt_tokens",       # OpenAI-compatible
)

_OUTPUT_FIELD_NAMES = (
    "output_tokens",           # Anthropic
    "candidates_token_count",  # Google
    "eval_count",              # Ollama
    "completion_tokens",       # OpenAI-compatible
)


def _extract_token_count(
    usage: dict[str, Any],
    field_names: tuple[str, ...],
) -> int | None:
    """Extract a token count from usage dict, trying each field name.

    Returns the first non-None value found, or None if no field matched.
    """
    for name in field_names:
        value = usage.get(name)
        if value is not None:
            return int(value)
    return None


class TokenTracker(BaseCallbackHandler):
    """LangChain callback handler that accumulates token counts.

    Normalizes token fields from Anthropic, Google, and Ollama into a
    unified ``input_tokens`` + ``output_tokens`` representation.

    Register as a callback on LLM invocations::

        tracker = TokenTracker()
        provider.invoke(prompt, callbacks=[tracker])

    After each call, ``tracker.total_tokens`` reflects the running total.
    """

    def __init__(self) -> None:
        super().__init__()
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._call_count: int = 0

    # -- Public properties ---------------------------------------------------

    @property
    def input_tokens(self) -> int:
        """Total input tokens accumulated across all LLM calls."""
        return self._input_tokens

    @property
    def output_tokens(self) -> int:
        """Total output tokens accumulated across all LLM calls."""
        return self._output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) across all LLM calls."""
        return self._input_tokens + self._output_tokens

    @property
    def call_count(self) -> int:
        """Number of LLM calls tracked."""
        return self._call_count

    def to_dict(self) -> dict[str, int]:
        """Return token breakdown as a dictionary.

        Returns
        -------
        A dict with keys: ``input_tokens``, ``output_tokens``,
        ``total_tokens``, ``call_count``.
        """
        return {
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self._call_count,
        }

    # -- LangChain callback --------------------------------------------------

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Accumulate tokens from an LLM response.

        Called by LangChain after each LLM call completes. Extracts
        token usage from the response's ``llm_output`` dict, normalizing
        across provider-specific field names.

        Parameters
        ----------
        response:
            A LangChain ``LLMResult`` with an ``llm_output`` dict
            containing a ``token_usage`` sub-dict.
        """
        self._call_count += 1

        usage = self._extract_usage(response)
        if usage is None:
            logger.warning(
                "LLM response missing token usage metadata; "
                "reporting zero tokens for this call"
            )
            return

        inp = _extract_token_count(usage, _INPUT_FIELD_NAMES)
        out = _extract_token_count(usage, _OUTPUT_FIELD_NAMES)

        if inp is None and out is None:
            logger.warning(
                "LLM response token_usage dict has no recognized "
                "token fields; reporting zero tokens for this call"
            )
            return

        self._input_tokens += inp or 0
        self._output_tokens += out or 0

    # -- Internal helpers ----------------------------------------------------

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any] | None:
        """Extract the token usage dict from an LLM response.

        Tries ``response.llm_output["token_usage"]`` (LangChain standard).
        Returns ``None`` if no usage metadata is available.
        """
        llm_output = getattr(response, "llm_output", None)
        if llm_output is None:
            return None

        if not isinstance(llm_output, dict):
            return None

        return llm_output.get("token_usage")  # type: ignore[no-any-return]
