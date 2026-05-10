# zebu-mcp

MCP server that exposes the Zebu paper-trading backend to Claude Code agents
as named tools. **Phase D, Wave 1** of the
[agent platform proposal](../docs/planning/agent-platform-proposal.md):
the foundation plus the complete read-tool surface. Write tools
(create-strategy, run-backtest, activate-strategy,
claim-exploration-task, ...) ship in Wave 2.

The server runs as a thin local **stdio** process — no network listener,
no central state, no shared infra. It auth's to a deployed Zebu backend
(local or `https://zebutrader.com`) using a personal API key and proxies
each MCP tool call into the matching REST endpoint.

## What you get

A FastMCP server registered under the name **`zebu`** with these tools:

| Tool | What it does |
|---|---|
| `list_supported_tickers` | Every ticker the platform has price data for |
| `get_current_price` | Latest observed price for one ticker |
| `get_price_history` | Historical price series (date range + interval) |
| `list_portfolios` | The user's paper-trading portfolios (paginated) |
| `get_portfolio_state` | Composite — metadata + balance + holdings |
| `list_strategies` | The user's saved strategies (paginated) |
| `get_strategy` | One strategy by ID |
| `list_backtests` | Backtest runs, optionally filtered by strategy |
| `get_backtest_result` | One backtest run + metrics |
| `list_active_strategies` | Strategies currently activated for live execution |
| `get_activation` | One activation by strategy or activation ID |
| `list_exploration_tasks` | The human → agent task queue |
| `get_exploration_task` | One exploration task by ID |

All list-returning tools are paginated and surface `total` / `limit` /
`offset` / `has_more` so the agent doesn't silently miss rows past the
default 20-item page.

## Install

The package lives in-tree at `mcp/` for now, but is structured so it can be
extracted into its own repo later. Velocity > extraction in Wave 1.

From the repo root:

```bash
cd mcp
uv sync --all-extras
```

This produces a `.venv` under `mcp/` with the runtime + dev deps.

## Get an API key

The MCP server authenticates as a Zebu user via a long-lived API key.
**You mint the key from a Clerk-authenticated session** (your normal logged-
in browser / API client):

```bash
# Replace <CLERK_BEARER_JWT> with the token from the logged-in UI:
curl -X POST https://zebutrader.com/api/v1/api-keys \
  -H "Authorization: Bearer <CLERK_BEARER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"label": "claude-code-laptop", "scopes": ["read"]}'
```

The response includes `raw_key` exactly once — store it somewhere safe.
The server only keeps the hash; if you lose the raw key, revoke and
re-mint.

For local dev (Clerk bypassed), point at `http://localhost:8000` instead.

## Configure

The MCP runtime is a stdio process and reads everything from environment
variables.

| Variable | Required | Default | What |
|---|---|---|---|
| `ZEBU_API_BASE_URL` | yes | — | Zebu API root, e.g. `https://zebutrader.com` or `http://localhost:8000`. Don't include `/api/v1` — the client appends it. |
| `ZEBU_API_KEY` | yes | — | Raw API key from `POST /api-keys`. Sent as `X-API-Key` on every request. |
| `ZEBU_API_TIMEOUT_SECS` | no | `30` | Per-request timeout. |

## Attach to Claude Code

Drop a server entry into your Claude Code MCP config — typically
`~/.claude.json` (the global file) or a project-local equivalent. The
exact filename depends on how Claude Code is configured on your machine.

```json
{
  "mcpServers": {
    "zebu": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/PaperTrade/mcp",
        "python",
        "-m",
        "zebu_mcp"
      ],
      "env": {
        "ZEBU_API_BASE_URL": "https://zebutrader.com",
        "ZEBU_API_KEY": "zk_..."
      }
    }
  }
}
```

Restart your Claude Code session; the tools should appear under the
`zebu` namespace (e.g. `zebu/list_portfolios`).

## Run locally without Claude Code

Useful for quick verification. The MCP Inspector ships with the
`mcp[cli]` package:

```bash
cd mcp
ZEBU_API_BASE_URL=http://localhost:8000 \
ZEBU_API_KEY=zk_... \
uv run --with "mcp[cli]" mcp dev src/zebu_mcp/__main__.py
```

That opens an interactive web UI you can fire tool calls from.

To just smoke-test stdio:

```bash
cd mcp
ZEBU_API_BASE_URL=http://localhost:8000 \
ZEBU_API_KEY=zk_... \
uv run python -m zebu_mcp
```

(That blocks on stdin waiting for the MCP framing protocol — Ctrl-C to
exit. It's not interactive without an MCP client driving it.)

## Develop

```bash
cd mcp
uv sync --all-extras
uv run ruff format .
uv run ruff check .
uv run pyright src tests
uv run pytest
```

The integration test (`tests/test_smoke.py`) is opt-in. Set
`ZEBU_MCP_INTEGRATION=1` in the environment with valid `ZEBU_API_BASE_URL`
+ `ZEBU_API_KEY` to actually hit a live Zebu backend.

## Roadmap

- **Wave 2** (next): write tools — `create_strategy`, `run_backtest`,
  `activate_strategy`, `deactivate_strategy`, `claim_exploration_task`,
  `submit_exploration_finding`, `note`. Per-tool scope enforcement (the
  API-key scopes set on the key — `read` / `trade` / `admin` — are
  carried at the auth layer; tools become aware of them in Wave 2).
- **Future research-context MCP** (separate composable server, not in
  this package): `web_search`, `fetch_news`, `fetch_url`,
  `get_earnings_calendar`. Intentionally split so the trading-data MCP
  stays focused.
- **Sidecar deployment** on Tim's personal Proxmox — graduates the server
  from "thin local stdio" to a long-lived process — once the tool
  surface stabilises (per Q6 of the proposal: never on company infra).

## Layout

```
mcp/
├── pyproject.toml         # zebu-mcp package config
├── README.md              # this file
├── src/zebu_mcp/
│   ├── __init__.py        # version, package metadata
│   ├── _version.py        # single source of truth for the version
│   ├── __main__.py        # CLI entry point
│   ├── server.py          # FastMCP bootstrap + lifespan
│   ├── client.py          # async httpx client for the Zebu REST API
│   ├── config.py          # env-driven config (ZebuMcpConfig)
│   ├── schemas.py         # typed Pydantic mirrors of API responses
│   └── tools/             # one module per tool domain
└── tests/                 # unit + opt-in integration tests
```
