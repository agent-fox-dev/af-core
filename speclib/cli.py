"""CLI entry point for the af-spec tool.

Minimal Click group providing the ``af-spec`` command. Full command set
will be implemented in spec 04.
"""

from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="speclib")
def main() -> None:
    """af-spec: AI-powered spec creation tool."""
