# Alpha Vantage MCP — strategic role alongside Zebu MCP

**Status**: design note, 2026-05-25.
**Premise**: we've just gained access to the AV premium tier and the AV MCP
server (`mcp.alphavantage.co`). Zebu MCP (`mcp/` in this repo, Phase D) is
already shipped. This note exists to clarify how the two interact, what each
should own, and what changes in our roadmap because both are now reachable
from the same Claude session.

## The two MCPs at a glance

|                        | Zebu MCP                                                            | Alpha Vantage MCP                                                             |
|------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------|
| Lives at               | `mcp/` in this repo (stdio, FastMCP)                                | `mcp.alphavantage.co` (HTTP) or `marketdata-mcp` (stdio uvx)                  |
| Exposes                | **App state + actions**: portfolios, strategies, backtests, activations, exploration tasks | **Market reality**: 122 tools across equities, options, fundamentals, news, commodities, indicators, macro |
| Identity & auth        | Per-user Zebu API key (minted via Clerk)                            | Per-user AV API key (each user brings their own)                              |
| Cost model             | Free (it's our backend)                                             | AV's per-user quota (rate-limited per minute / per day)                       |
| When the agent calls it | "What strategies do I have? Run a backtest. Create a strategy."     | "What does AAPL look like? Any recent news? RSI? Options chain? Fundamentals?" |

**One-liner**: Zebu MCP is *the app*. AV MCP is *the world the app trades in*.
Use Zebu MCP to *act*; use AV MCP to *research*.

## Why this is a good complement

Three reasons to keep them separate rather than re-exposing AV through Zebu:

1. **Surface area without code.** AV ships 122 tools today — news sentiment,
   60+ technical indicators, options, fundamentals, commodities, macro
   indicators. Wrapping any meaningful subset of that inside Zebu would be
   months of work. The MCP gateway gives us all of it for free.
2. **Quota is the user's, not ours.** Every AV MCP call hits the user's own
   AV key, not a shared Zebu-side budget. That keeps Zebu cheap to operate
   and makes the cost model fair: heavy researchers pay AV more, light users
   pay AV nothing extra. We don't have to think about quota engineering.
3. **Updates without us.** When AV adds a new tool (e.g. earnings call
   transcripts, which they recently shipped), every user gets it the next
   time their MCP server restarts. No Zebu release needed.

The trade-off is that the agent has to **decide which server to call** for
a given question — which is a real prompt-engineering surface, not a free
lunch. See the "Design implications" section below.

## Who calls which, and when

Three personas for the immediate future:

### 1. Us (orchestrating builds + research)

This is the current state — you and me in this very conversation. We use AV
MCP for:

- Empirical validation of provider behaviour (e.g. today's "is AV free
  actually 100 days?" check that motivated this whole thread).
- Spec-ing new strategies: "what indicators would make sense for a
  mean-reversion strategy on tickers in {Energy, Tech}?"
- Research-before-design: "what fundamental fields does AV expose? Should
  the strategy editor surface PE ratio? Earnings dates?"

We **don't** use Zebu MCP much in this orchestration mode — we're modifying
its code more often than calling it. That flips when we're testing the
deployed app.

### 2. A Zebu user via their own Claude (the medium-term goal)

A user installs Claude Code locally, drops `.mcp.json` snippets for both
servers, supplies their AV key + their Zebu key, and gets:

- "Show me my portfolio. Has anything happened in the news for my holdings
  today?" — Zebu MCP for the holdings, AV MCP for `NEWS_SENTIMENT`.
- "Backtest a moving-average crossover on these 5 tickers. Then compare
  Sharpe to a baseline buy-and-hold." — Zebu MCP for both, no AV needed.
- "Run a backtest of an RSI strategy on AAPL. Pull the RSI values from AV
  directly so we can also evaluate alternate window sizes without storing
  more data." — Zebu MCP for the backtest, AV MCP for the off-line RSI
  comparison.

This is the right architecture: each MCP is the user's own tool, talking to
its own service with its own credentials. We host *zebutrader.com*; we
don't host their AV access. AV's keys are theirs to manage.

### 3. The autonomous agent loop (Phase L+ direction)

The longer-term direction in `agent-platform-next-steps.md` is letting Zebu
itself run agentic backtests / live executions. *Today* that agent's only
data source is Zebu's own price cache. With premium AV available, we have
the option to let the agent **call AV directly during execution** — for
news-sentiment-aware entries, fundamentals-aware sizing, indicator panels
that aren't worth caching. That's a deliberate scope expansion to defer
until backtest-with-agent is solid (Phase L is mid-flight).

Notably: this is the one place where it'd be *us* paying AV (Zebu-side
key), not the user. Stay cautious about adding it without a quota plan.

## Design implications for Zebu

A few principles to apply going forward:

1. **Don't duplicate AV in Zebu's MCP.** If the agent asks "what's the news
   on AAPL?", the right answer is *use AV MCP*, not "build a news endpoint
   in Zebu". The MCP gateway is the dependency we're now leaning on.
2. **Do cache what's worth caching.** Price history, daily bars — Zebu owns
   these because we want them shared across backtests and across users.
   Fundamentals, news, real-time options — these can stay outside, fetched
   per-conversation by the user's own AV MCP.
3. **Ticker validation** (the new endpoint in PR #313) currently calls AV
   internally via the backend. That's the right call — it's a write path
   we want to gate server-side. But if we ever want a "search for a ticker
   as I type" UI, that should call AV MCP from the *user's* client, not
   ours. Cost stays local to whoever is exploring.
4. **Expose hints, not data.** A future Zebu MCP improvement: a tool like
   `recommend_market_data_for_strategy(strategy_id)` that returns "for
   this MA-crossover, you'll want EMA(fast), EMA(slow), and ATR for stop
   sizing — those are AV tools `EMA` and `ATR`." This makes the agent
   composable across the two MCPs without our needing to wrap AV.
5. **Validate users have AV configured.** Docs / onboarding should make it
   crystal-clear: "to use Claude with Zebu effectively, install AV MCP
   too; here's the snippet." Zebu without AV works for trading-only flows;
   research is crippled without AV.
6. **No multi-tenanting our AV key.** Don't share our admin AV key with
   users via Zebu's MCP. Each user brings their own key — full stop. This
   matches our broader stance that user-supplied credentials live in the
   user's local Claude config, never on our servers.

## Open questions to think about

These don't need answers today but are worth tracking:

- **Tooling surface in `recommend_market_data_for_strategy`** — what would
  this return? A list of AV tool names + suggested params? A natural-
  language description? Worth a spike when we touch the strategy-editor
  UX again.
- **Strategy editor with AV-derived indicator picker.** Today the supported
  strategy types are hard-coded (`BUY_AND_HOLD`, `DCA`, `MA_CROSSOVER`).
  With AV exposing 60+ indicators, do we open the strategy params up to
  arbitrary indicator names? That's a meaningful UX shift — probably a
  Phase M or N consideration, not now.
- **Backtest with off-cache indicators.** If a backtest needs RSI(14) but
  we only store daily bars, do we compute RSI in-process or call AV's RSI
  tool? In-process is cheaper and deterministic; AV-call gives us
  multi-resolution flexibility. For backtests, lean in-process. For live
  exploration, AV is fine.
- **News-sentiment-driven backtests.** A real Phase L+ idea: the agent
  reads news headlines + sentiment scores per day, decides positioning.
  Achievable today through AV's `NEWS_SENTIMENT` tool. Not in scope for
  this conversation, but it's now *possible* in a way it wasn't a week
  ago.

## How AV MCP is wired up in this repo

For Claude Code running in this repo, the AV MCP is now in `.mcp.json` at
the repo root with `${ALPHA_VANTAGE_API_KEY}` substitution. You need to:

1. Have your AV key in your shell env when launching Claude Code:
   ```bash
   export ALPHA_VANTAGE_API_KEY="..."          # premium key from 1Password
   ```
   (or use `direnv` / `op run --env-file=.env -- claude` for hands-off).
2. After launching Claude Code in this repo, you should see `alphavantage`
   in the MCP servers list. The tools appear under the `mcp__alphavantage__*`
   namespace.

For end users who install Zebu's MCP later, the same pattern applies — they
add the AV MCP block to their own `.mcp.json` / Claude config with their
own AV key.

## References

- AV MCP docs: https://mcp.alphavantage.co/
- Tool inventory: 122 tools across 9 categories (time series, options,
  Alpha Intelligence, fundamentals, forex, crypto, commodities, economic
  indicators, technical indicators).
- Zebu MCP: `mcp/README.md`.
- Agent-platform forward plan: `docs/planning/agent-platform-next-steps.md`.
