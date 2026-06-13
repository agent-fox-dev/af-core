"""Parse spec pack folders into structured models.

Loads the four artifacts (requirements.json, test_spec.json, tasks.json,
prd.md) from a spec pack directory and returns a ``ParsedSpec`` containing
the parsed pydantic models alongside the raw PRD markdown text.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from afspec.models import (  # type: ignore[import-untyped]
    Requirements,
    SpecMeta,
    Tasks,
    TestSpec,
)

from coder.errors import SpecParseError
from coder.models import ParsedSpec

logger = logging.getLogger(__name__)

# Required JSON artifact files that must be present in every spec pack.
_REQUIRED_JSON_FILES: list[tuple[str, Any]] = [
    ("requirements.json", Requirements),
    ("test_spec.json", TestSpec),
    ("tasks.json", Tasks),
]


class SpecParser:
    """Parse a spec pack directory into a ``ParsedSpec`` model.

    Usage::

        parser = SpecParser()
        parsed = parser.parse(meta)
    """

    def parse(self, meta: SpecMeta) -> ParsedSpec:
        """Load and parse all artifacts from a spec folder.

        Parameters
        ----------
        meta:
            Discovery metadata pointing to the spec pack directory.

        Returns
        -------
        ParsedSpec
            A frozen model containing all parsed artifacts.

        Raises
        ------
        SpecParseError
            If a required JSON file is missing or contains invalid JSON.
        """
        spec_dir = Path(meta.dir)

        # Load each required JSON artifact.
        artifacts: dict[str, object] = {}
        for filename, model_cls in _REQUIRED_JSON_FILES:
            artifacts[filename] = self._load_json(
                spec_dir, filename, model_cls, meta.spec_name,
            )

        # Load prd.md (optional — missing file yields empty string + warning).
        prd_text = self._load_prd(spec_dir, meta.spec_name)

        return ParsedSpec(
            meta=meta,
            requirements=artifacts["requirements.json"],  # type: ignore[arg-type]
            test_spec=artifacts["test_spec.json"],  # type: ignore[arg-type]
            tasks=artifacts["tasks.json"],  # type: ignore[arg-type]
            prd_text=prd_text,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(
        spec_dir: Path,
        filename: str,
        model_cls: Any,
        spec_name: str,
    ) -> Any:
        """Load and validate a single JSON artifact file.

        Raises ``SpecParseError`` if the file is missing or contains
        invalid JSON.
        """
        path = spec_dir / filename

        if not path.is_file():
            raise SpecParseError(
                f"Missing required file: {filename}",
                spec_name=spec_name,
                file_path=str(path),
            )

        text = path.read_text(encoding="utf-8")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SpecParseError(
                f"Invalid JSON in {filename}",
                spec_name=spec_name,
                file_path=str(path),
                detail=str(exc),
            ) from exc

        try:
            return model_cls.model_validate(data)
        except Exception as exc:
            raise SpecParseError(
                f"Validation error in {filename}",
                spec_name=spec_name,
                file_path=str(path),
                detail=str(exc),
            ) from exc

    @staticmethod
    def _load_prd(spec_dir: Path, spec_name: str) -> str:
        """Load prd.md as raw text.

        Returns an empty string and logs a warning if the file is missing.
        """
        path = spec_dir / "prd.md"

        if not path.is_file():
            logger.warning(
                "Missing prd.md for spec '%s' — using empty string",
                spec_name,
            )
            return ""

        return path.read_text(encoding="utf-8")
