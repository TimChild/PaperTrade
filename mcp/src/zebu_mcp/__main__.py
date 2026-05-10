"""CLI entry point: ``python -m zebu_mcp`` (or ``uvx zebu-mcp``).

Reads env config, builds the server, and runs on stdio. Errors during
config / startup are written to stderr (so Claude Code surfaces them in
the MCP server log) and the process exits non-zero.
"""

from __future__ import annotations

import sys

from zebu_mcp.config import ConfigError
from zebu_mcp.server import run_stdio


def main() -> None:
    """Entry point used by both ``python -m zebu_mcp`` and the console script."""
    try:
        run_stdio()
    except ConfigError as exc:
        # Stderr so Claude Code's MCP server log surfaces it. Exit 2 to
        # distinguish config errors from runtime crashes (which exit 1).
        print(f"zebu-mcp: configuration error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
