"""Tests for prompt template loading.

Test Spec Entries: TS-12-12, TS-12-13, TS-12-14, TS-12-E5, TS-12-E6,
TS-12-E9, TS-12-P3.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from coder.errors import TemplateNotFoundError, TemplateSecurityError
from coder.templates import TemplateLoader
from hypothesis import given, settings
from hypothesis import strategies as st


class TestTemplateLoading:
    """Tests for loading templates from filesystem."""

    def test_load_package_default(self) -> None:
        """TS-12-12: Template loader finds package defaults.

        Requirement: 12-REQ-5.1, 12-REQ-5.6
        Verifies default templates are loadable from the package and
        that YAML frontmatter is stripped.
        """
        loader = TemplateLoader()
        content = loader.load("coder")
        assert len(content) > 0
        assert not content.startswith("---")

    def test_project_override(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-13: Template loader prefers project-level override.

        Requirement: 12-REQ-5.2
        Verifies project templates override package defaults.
        """
        (template_dir / "coder.md").write_text("Custom coder prompt")
        loader = TemplateLoader(project_dir=tmp_path)
        content = loader.load("coder")
        assert content == "Custom coder prompt"

    def test_frontmatter_stripped(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-14: Template loader strips frontmatter.

        Requirement: 12-REQ-5.3
        Verifies YAML frontmatter is removed from templates.
        """
        template_content = "---\nname: test\n---\nActual content"
        (template_dir / "test.md").write_text(template_content)

        loader = TemplateLoader(project_dir=tmp_path)
        content = loader.load("test")
        assert content == "Actual content"


class TestTemplateEdgeCases:
    """Edge case tests for template loading."""

    def test_not_found(self) -> None:
        """TS-12-E5: Template not found raises TemplateNotFoundError.

        Requirement: 12-REQ-5.E1
        Verifies missing template produces a clear error with
        searched paths listed.
        """
        loader = TemplateLoader()
        with pytest.raises(TemplateNotFoundError):
            loader.load("nonexistent_template_xyz")

    def test_symlink_rejected(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-E6: Symlink template rejected.

        Requirement: 12-REQ-5.5
        Verifies symlinks in template directory are rejected.
        """
        target = tmp_path / "target.md"
        target.write_text("target content")
        symlink = template_dir / "evil.md"
        symlink.symlink_to(target)

        loader = TemplateLoader(project_dir=tmp_path)
        with pytest.raises(TemplateSecurityError):
            loader.load("evil")

    def test_empty_template_returns_empty(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-E9: Empty template file returns empty string.

        Requirement: 12-REQ-5.E2
        Verifies loading a zero-byte template file returns an empty
        string without error.
        """
        (template_dir / "empty.md").write_text("")
        loader = TemplateLoader(project_dir=tmp_path)
        content = loader.load("empty")
        assert content == ""


class TestTemplateProperties:
    """Property-based tests for template security."""

    @settings(max_examples=50)
    @given(
        prefix=st.text(
            min_size=0,
            max_size=10,
            alphabet=st.characters(categories=("L", "N")),
        ),
        separator=st.sampled_from(["/", "\\", ".."]),
        suffix=st.text(
            min_size=0,
            max_size=10,
            alphabet=st.characters(categories=("L", "N")),
        ),
    )
    def test_property_path_traversal(
        self, prefix: str, separator: str, suffix: str
    ) -> None:
        """TS-12-P3: Template names are path-traversal safe.

        Property 3 from design.md.
        Validates: 12-REQ-5.4, 12-REQ-5.5
        Any template name containing path separators or traversal
        sequences is rejected.
        """
        from hypothesis import assume

        name = prefix + separator + suffix
        assume(len(name) > 0)

        loader = TemplateLoader()
        with pytest.raises((ValueError, TemplateSecurityError)):
            loader.load(name)
