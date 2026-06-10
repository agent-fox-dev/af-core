"""afspec — spec format models, validation, rendering, and I/O.

Stub package. The real afspec (speclib-python) provides spec-format v1.2
models and operations.
"""

from __future__ import annotations

from afspec.validation import ValidationError, validate_artifact

__version__ = "0.1.0"

__all__ = ["ValidationError", "validate_artifact"]
