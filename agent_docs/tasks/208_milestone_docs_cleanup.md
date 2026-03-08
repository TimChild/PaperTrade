# Task 208: Milestone Documentation Cleanup

## Context

We just completed a major milestone — Phase 4 (Trading Strategies & Backtesting) backend + frontend are done and deployed. Many project-level docs are significantly out of date. This is a milestone-close cleanup to bring everything current.

**Current reality (March 8, 2026):**
- 835 backend tests, 311 frontend tests (1,146 total)
- Phase 1-4 all complete and deployed to production (192.168.4.112)
- Features: Portfolio CRUD, trading (BUY/SELL), real-time prices, historical data, analytics charts, backtesting with 3 strategy types, strategy comparison UI
- Stack: Python 3.13+/FastAPI/SQLModel backend, React/TypeScript/TanStack Query frontend
- Auth: Clerk. Monitoring: Grafana Cloud. Cache: Redis. DB: PostgreSQL (prod), SQLite (dev)
- Production domain: zebutrader.com

## Scope

### 1. BACKLOG.md — Heavy Rewrite

The current file is ~210 lines, of which ~50% are completed items. It should be:
- **Remove all completed items** (they belong in PROGRESS.md, not here)
- **Remove the "Recently Completed" and "Older Completed Items" sections entirely**
- **Keep only actual backlog items** that are NOT done yet
- Known remaining items:
  - Skipped scheduler tests (4 tests)
  - Admin authentication TODOs on analytics endpoints
  - Database indexes (Transaction.portfolio_id, Transaction.timestamp)
  - Bundle size analysis
  - Future: WebSocket integration, multiple currencies, social/sharing features
  - Live strategy execution (next major feature)
  - CD pipeline automation
  - Error monitoring (Sentry or alternative)
  - S&P 500 benchmark comparison in backtest charts
- Target: ~50-80 lines, clean categories (Features, Technical Debt, Infrastructure)

### 2. PROGRESS.md — Update Status

Current file says "Phase 2 Complete" at the top (!). Needs:
- Update the status table to show all phases complete through Phase 4
- Update test counts (835 backend, 311 frontend)
- The detailed session-by-session history can be trimmed — keep the most recent work and summarize older work more briefly
- Add the Phase 4 and frontend backtesting UI work

### 3. README.md — Update Feature List

Current README claims SELL trades are "Phase 3 - Q1 2026" and backtesting is "Phase 4" as if they're future work. Fix:
- Update the status line at the top (currently says "Phase 2 Complete")
- Update the feature checklist to show SELL, analytics, backtesting, strategy comparison as complete
- Update documentation links if any have moved
- Keep it concise — the README should be an accurate overview, not a changelog

### 4. resume-from-here.md — Update

This file should reflect the current state after PR #207 (frontend backtesting UI) was merged. Update to note:
- PR #207 merged — frontend backtesting UI complete
- Current focus areas: docs cleanup, CD pipeline, live strategy execution
- Remove Phase 4 implementation details (they're done)

### 5. Move session_handoff.md

- Move `agent_docs/procedures/session_handoff.md` → `agent_docs/reusable/session_handoff.md`
- Delete `agent_docs/procedures/README.md` (it's just a redirect page to docs/testing/)
- Delete the `agent_docs/procedures/` directory if empty after the move
- Search for any references to the old path and update them (check archived docs too, but only update non-archived references)

### 6. .github/copilot-instructions.md — Light Touch

This file is generally good but may need small updates:
- Verify the test count references are current (if any)
- Verify the technology stack section is accurate
- Do NOT restructure or shorten — this file is actively used by all agents
- Only fix things that are factually wrong

## Acceptance Criteria

1. ✅ BACKLOG.md contains only incomplete items, organized clearly
2. ✅ PROGRESS.md status table reflects all phases complete through Phase 4
3. ✅ README.md feature list is accurate (backtesting, strategies shown as complete)
4. ✅ resume-from-here.md reflects post-PR #207 state
5. ✅ session_handoff.md moved to agent_docs/reusable/
6. ✅ agent_docs/procedures/ directory removed
7. ✅ No broken internal links
8. ✅ All docs use professional, direct tone — no conversational fluff
9. ✅ `task quality` passes (no pre-commit hook failures on markdown)
