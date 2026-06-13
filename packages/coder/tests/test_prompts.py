"""Tests for prompt assembly.

Test Spec Entries: TS-12-15, TS-12-16, TS-12-27, TS-12-E13,
TS-12-P4, TS-12-P5.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from coder.prompts import PromptAssembler
from coder.templates import TemplateLoader
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPromptAssembly:
    """Tests for 3-layer prompt composition."""

    def test_three_layers(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-15: Prompt assembler composes three layers.

        Requirement: 12-REQ-6.1
        Verifies 3-layer prompt assembly with correct ordering:
        base (agent.md) + persona (coder.md) + task context.
        """
        (template_dir / "agent.md").write_text("Base")
        (template_dir / "coder.md").write_text("Persona")

        loader = TemplateLoader(project_dir=tmp_path)
        assembler = PromptAssembler(loader)
        result = assembler.assemble(
            persona="coder", task_context="Context"
        )
        assert result == "Base\n\nPersona\n\nContext"

    def test_skip_base(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-16: Prompt assembler skips missing base profile.

        Requirement: 12-REQ-6.2
        Verifies assembly works without a base profile (agent.md).
        """
        (template_dir / "coder.md").write_text("Persona")
        # No agent.md exists

        loader = TemplateLoader(project_dir=tmp_path)
        assembler = PromptAssembler(loader)
        result = assembler.assemble(
            persona="coder", task_context="Context"
        )
        assert result == "Persona\n\nContext"

    def test_assemble_accepts_variables(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-27: assemble_prompt accepts persona, context, and variables.

        Requirement: 12-REQ-6.4
        Verifies assemble() accepts persona name, task context string,
        and an optional variables dictionary, returning the assembled
        prompt with substitutions applied.
        """
        (template_dir / "agent.md").write_text("Base $project")
        (template_dir / "coder.md").write_text("Persona")

        loader = TemplateLoader(project_dir=tmp_path)
        assembler = PromptAssembler(loader)
        result = assembler.assemble(
            persona="coder",
            task_context="Context",
            variables={"project": "TestProject"},
        )
        assert "TestProject" in result
        assert "Persona" in result
        assert "Context" in result


class TestPromptEdgeCases:
    """Edge case tests for prompt assembly."""

    def test_extra_variables_ignored(
        self, tmp_path: Path, template_dir: Path
    ) -> None:
        """TS-12-E13: Extra variables key ignored.

        Requirement: 12-REQ-6.E1
        Verifies extra keys in variables dict do not cause errors.
        """
        (template_dir / "coder.md").write_text("Persona")

        loader = TemplateLoader(project_dir=tmp_path)
        assembler = PromptAssembler(loader)
        result = assembler.assemble(
            persona="coder",
            task_context="Ctx",
            variables={"extra": "val"},
        )
        assert "Ctx" in result


class TestPromptProperties:
    """Property-based tests for prompt assembly."""

    @settings(max_examples=20)
    @given(
        persona_text=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                categories=("L",),
                min_codepoint=65,
                max_codepoint=90,
            ),
        ),
        task_context=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                categories=("L",),
                min_codepoint=97,
                max_codepoint=122,
            ),
        ),
    )
    def test_property_layer_order(
        self, persona_text: str, task_context: str
    ) -> None:
        """TS-12-P4: Prompt assembly preserves layer order.

        Property 4 from design.md.
        Validates: 12-REQ-6.1, 12-REQ-6.2
        The assembled prompt always contains persona content before
        task context.
        """
        from hypothesis import assume

        assume(persona_text != task_context)
        assume(task_context not in persona_text)
        assume(persona_text not in task_context)

        with tempfile.TemporaryDirectory() as tmpdir:
            tpl_dir = Path(tmpdir) / ".coder" / "templates"
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "test_persona.md").write_text(persona_text)

            loader = TemplateLoader(project_dir=Path(tmpdir))
            assembler = PromptAssembler(loader)
            result = assembler.assemble(
                persona="test_persona", task_context=task_context
            )

            assert persona_text in result
            assert task_context in result
            assert result.index(persona_text) < result.index(
                task_context
            )

    @settings(max_examples=20)
    @given(
        known_val=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                categories=("L",),
                min_codepoint=65,
                max_codepoint=90,
            ),
        ),
    )
    def test_property_safe_substitution(
        self, known_val: str
    ) -> None:
        """TS-12-P5: Safe substitution leaves unknown placeholders.

        Property 5 from design.md.
        Validates: 12-REQ-6.3, 12-REQ-6.E1
        Template substitution replaces known variables and leaves
        unknown $placeholders unchanged.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tpl_dir = Path(tmpdir) / ".coder" / "templates"
            tpl_dir.mkdir(parents=True)
            (tpl_dir / "subst_persona.md").write_text(
                "Hello $known, meet $unknown"
            )

            loader = TemplateLoader(project_dir=Path(tmpdir))
            assembler = PromptAssembler(loader)
            result = assembler.assemble(
                persona="subst_persona",
                task_context="Context",
                variables={"known": known_val},
            )

            assert known_val in result
            assert "$unknown" in result
