"""Zebu MCP server.

Exposes the Zebu paper-trading backend as named MCP tools so Claude Code
agents can call it directly (Phase D, Wave 1 — read tools only). The
package is intentionally self-contained — it talks to Zebu over HTTP using
an API key and shares no code with the FastAPI service so the package
can be lifted out into a standalone repo later if we choose.

See ``mcp/README.md`` for install + Claude Code attach instructions.
"""

from zebu_mcp._version import __version__

__all__ = ["__version__"]
