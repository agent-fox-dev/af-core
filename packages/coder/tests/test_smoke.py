"""Integration smoke tests for coder package.

Test Spec Entries: TS-12-SMOKE-1, TS-12-SMOKE-2.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from coder.cli import cli
from coder.prompts import PromptAssembler
from coder.templates import TemplateLoader


class TestCLISmoke:
    """Integration smoke tests for CLI invocation path."""

    def test_smoke_cli_resolves_provider(
        self,
        tmp_path: Path,
        fake_anthropic_key: str,
    ) -> None:
        """TS-12-SMOKE-1: CLI run resolves provider.

        Execution Path 1 from design.md.
        Verifies the full CLI invocation path from command to provider
        resolution. The real ProviderRegistry.resolve() must execute
        (not mocked). Only the LLM invoke() is mocked.
        """
        campaign_dir = tmp_path / "campaign"
        campaign_dir.mkdir()

        runner = CliRunner(mix_stderr=False)

        # Mock only the LLM invoke call, not provider creation
        with patch(
            "coder.providers.AnthropicProvider.invoke"
        ):
            result = runner.invoke(
                cli,
                [
                    "run",
                    str(campaign_dir),
                    "--model",
                    "claude-opus-4-6",
                ],
            )

        assert result.exit_code == 0


class TestPromptAssemblySmoke:
    """Integration smoke tests for prompt assembly."""

    def test_smoke_prompt_assembly_e2e(self) -> None:
        """TS-12-SMOKE-2: Prompt assembly end-to-end.

        Execution Path 2 from design.md.
        Verifies prompt assembly loads real templates and composes
        them correctly. Real filesystem reads must execute (no
        TemplateLoader.load mock).
        """
        loader = TemplateLoader()
        assembler = PromptAssembler(loader)
        result = assembler.assemble(
            persona="coder", task_context="Implement X"
        )

        assert "Implement X" in result
        # Other layers (base + persona) should add content
        assert len(result) > len("Implement X")
