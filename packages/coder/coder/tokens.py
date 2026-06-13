"""Token tracking callback handler for LLM calls.

Accumulates token counts across providers (Anthropic, Google, Ollama)
using LangChain's BaseCallbackHandler.

Implements Requirements:
    15-REQ-2.1 (accumulate tokens), 15-REQ-2.2 (normalize providers),
    15-REQ-2.3 (total_tokens, to_dict), 15-REQ-2.4 (callback registration),
    15-REQ-2.E1 (missing metadata).

Note: Stub module for import compatibility (task group 1).
      Full implementation in task group 3.
"""

from __future__ import annotations

from langchain_core.callbacks import BaseCallbackHandler


class TokenTracker(BaseCallbackHandler):
    """LangChain callback handler that accumulates token counts.

    Stub — raises NotImplementedError until task group 3.
    """

    def __init__(self) -> None:
        raise NotImplementedError("TokenTracker not yet implemented")

    @property
    def input_tokens(self) -> int:
        """Total input tokens accumulated."""
        raise NotImplementedError

    @property
    def output_tokens(self) -> int:
        """Total output tokens accumulated."""
        raise NotImplementedError

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        raise NotImplementedError

    @property
    def call_count(self) -> int:
        """Number of LLM calls tracked."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, int]:
        """Return token breakdown as dictionary."""
        raise NotImplementedError
