---
name: audit-mode
description: Run a specialist agent in "audit mode" — produce a prioritized findings report at agent_docs/audits/YYYY-MM-DD/<slug>.md instead of code changes. Defines the report format, P0/P1/P2/P3 calibration, slug convention, and multi-agent dispatch pattern. Use when scoping or executing a Phase-B-style codebase audit cycle.
---

# Audit Mode

Codifies how a specialist agent runs **as an auditor**: read code, produce a prioritized findings report, write **no code changes**. Distilled from the 2026-05-09 12-dimension Phase B1 audit pass that demonstrated this pattern.

## When this skill applies

The orchestrator is dispatching a specialist agent (`architect`, `backend-swe`, `frontend-swe`, `quality-infra`, `refactorer`, `docs-refactorer`) **with the qualifier "audit mode"** — for example:

- `backend-swe (audit mode): backend code quality review`
- `architect + docs-refactorer (audit mode): Claude infrastructure dimension`
- `quality-infra (audit mode): test quality and flakiness`

If the task is "implement X" or "refactor Y", this skill does **not** apply — that's normal specialist work. Audit mode is exclusively a read-and-report mode.

## Inviolable rules (audit-vs-fix discipline)

- **No code changes.** The audit produces one or two markdown files. No `git add`, no edits to `backend/`, `frontend/`, `docs/`, `.claude/`, etc. (Exception: writing the report itself under `agent_docs/audits/`.)
- **No PRs.** Hand the report back to the orchestrator. Fixes happen in **separate Wave-style PRs** dispatched after the audit closes (see `agent_docs/audits/2026-05-09/SUMMARY.md` for the wave pattern).
- **Cite specifics.** Every finding cites `path:line` (or `path:line-range`). A finding without a citation is not actionable.
- **Calibrate; don't drown.** 5–15 findings per dimension is the target band (see calibration section). If you have 40, you're either too granular or auditing too much; split the dimension or raise the bar.

## Pre-work for an audit agent

Before reading the audit-target code, read in order:

1. `CLAUDE.md` — the project's hard rules (no `Any`, Clean Architecture, behavior-focused tests). These are the standards you're auditing against.
2. The relevant agent persona under `.claude/agents/` — for example, the `backend-swe` audit reads `.claude/agents/backend-swe.md` to know what "good" looks like for that lens. (When a dimension has co-auditors — e.g., `architect + docs-refactorer` — read both.)
3. **The previous audit report at the same dimension if one exists** — `ls agent_docs/audits/` and check whether your `<slug>.md` was audited before. Cite it as the prior baseline; flag findings that recurred.
4. The proposal section that scoped the audit — for Phase B1 that's `docs/planning/agent-platform-proposal.md` §B1.

This is the audit-mode equivalent of the `before-starting-work` skill — same intent, audit-shaped.

## Directory layout

```
agent_docs/audits/<YYYY-MM-DD>/
├── <slug-1>.md          # one report per dimension
├── <slug-2>.md
├── ...
└── SUMMARY.md           # consolidator written by the orchestrator
```

- The date is the **dispatch date** of the audit cycle, not the per-agent finish date. All 12 dimensions in a cycle share one date directory.
- Each dimension is **one file**, slug-named.
- `SUMMARY.md` is owned by the orchestrator and consolidates per-file P-counts, top concerns, and an execution wave plan. Audit agents do not write it.

## Slug convention

3–5 character dimension slug, used in the filename and as the `[P0-<slug>-N]` finding-ID prefix. Established slugs from the 2026-05-09 cycle:

| Dimension | Slug | Filename |
|---|---|---|
| Architecture | `arch` | `architecture.md` |
| Backend code quality | `bcode` | `backend-code-quality.md` |
| Frontend code quality | `fcode` | `frontend-code-quality.md` |
| Test quality & flakiness | `tests` | `test-quality.md` |
| CI infrastructure | `ci` | `ci-infrastructure.md` |
| Domain model | `domain` | `domain-model.md` |
| API design | `api` | `api-design.md` |
| Security | `sec` | `security.md` |
| Database | `db` | `database.md` |
| Documentation | `docs` | `documentation.md` |
| Dependencies | `deps` | `dependencies.md` |
| Claude infrastructure | `claude` | `claude-infra.md` |

For a new dimension not in this table, pick a slug that is unique within the audit cycle and short (lowercase, no spaces). Update this table when a new dimension is added.

## Report structure (per-dimension file)

Use this exact skeleton. The 2026-05-09 reports vary slightly in section nesting, but every one of them carries this content:

```markdown
# <Title> Audit — Phase <N>

- **Auditor**: <agent-name> (audit mode)         # e.g. `backend-swe (audit mode)` or `architect + refactorer`
- **Slug**: `<slug>`
- **Date**: YYYY-MM-DD
- **Scope**: <paths or modules audited — be specific>

## Summary

| Priority | Count |
|---|---:|
| P0 | <n> |
| P1 | <n> |
| P2 | <n> |
| P3 | <n> |
| **Total** | **<n>** |

**Top concern (one sentence)**: <the single most important finding, in plain English, naming the affected path>.

<Optional 1–2 paragraph framing — what's healthy vs. what isn't.>

## Findings

### P0 — <one-line description of what P0 means in this dimension>

#### [P0-<slug>-1] <Short title>

- **Evidence**: `path/to/file.py:LINE` — `code or pattern excerpt`
- **Why it matters**: <what breaks, who pays, what phase is blocked>
- **Recommended fix**: <concrete enough that a fix-PR can be scoped from it>

#### [P0-<slug>-2] ...

### P1 — <one-line description>

#### [P1-<slug>-1] ...

### P2 — <one-line description>

### P3 — <one-line description>

## Notable strengths (what's GOOD)

<3–7 bullets of "this is exemplary, don't disturb it" — see calibration below.>

## Estimated total fix effort

- P0 (collectively): ~Nh
- P1 (collectively): ~Nh
- P2 (collectively): ~Nh
- P3 deferred
```

Real examples to model on: `agent_docs/audits/2026-05-09/architecture.md` (clean structure, 11 findings, exemplary), `agent_docs/audits/2026-05-09/security.md` (heavier prose, also fine), `agent_docs/audits/2026-05-09/claude-infra.md` (the report that produced *this* skill).

## Priority calibration (P0 / P1 / P2 / P3)

The single hardest part of audit mode is calibrating consistently. These rules are derived from how the 2026-05-09 cycle classified its 137 findings:

### P0 — Critical: blocks future work or is actively broken

A finding is P0 if **at least one** of:

- **Production-exposed risk right now.** Example: `security.md` P0-1 — two unauthenticated admin endpoints reachable on `https://zebutrader.com`.
- **Blocks the next major phase.** Example: `architecture.md` P0-1 — Domain → Application import cycle; every Phase C/F live executor will inherit it.
- **Actively misleads a future agent or developer.** Example: `claude-infra.md` P0-1 — `architecture_plans/` referenced as a real directory but doesn't exist; `documentation.md` P0-1 — README onboarding flow broken end-to-end.
- **Critical CVE / auth-bypass class advisory** with a fix available. Example: `dependencies.md` P0-1 — Clerk SDK middleware route-protection bypass.
- **Silent data corruption / cross-tenant write bleed.** Example: `security.md` P0-2 — backfill endpoint takes `CurrentUserDep` but ignores it.

P0 should be **rare and unambiguous**. The 2026-05-09 cycle had 24 P0s across 12 dimensions (~2/dimension); some dimensions (`fcode`, `domain`) had **zero** P0s and that's the right answer when the surface is healthy. Don't manufacture a P0 to look thorough.

### P1 — High: foundation refactors that make the next phase materially easier

A finding is P1 if it is **structural debt that compounds** as the codebase grows, but it is not actively breaking anything today. Examples:

- Primitive obsession on a high-traffic path that the next phase will multiply (`domain.md` P1-1 — `TradeSignal` uses raw `str` ticker / raw `Decimal`).
- Duplicated validation logic that will drift (`bcode.md` P1-3 — strategy parameter validation in two places with subtly different rules).
- Missing test coverage on a path the next phase will mirror (`tests.md` P1 — `BacktestExecutor` has 4 unit tests over 474 LOC; Phase C's live executor will mirror its structure).
- Missing pagination / API hygiene on endpoints that will scale under the next phase (`api.md` P1-3).

P1s should be **fixable in a focused PR or two**. If a P1 needs three weeks of refactoring it's probably misclassified — re-scope it as several smaller P1s or accept it as a P2 with a deferral note.

### P2 — Medium: worth fixing, not blocking

P2 is **opportunistic cleanup** — code smells, minor inconsistencies, hardening that pays off but isn't urgent. Examples:

- `arch.md` P2-1 — `BacktestRun.initial_cash` is `Decimal` not `Money` (the wrap happens at the use-case layer; the entity hasn't caught up).
- `sec.md` P2-2 — CORS `allow_methods=["*"], allow_headers=["*"]` paired with `allow_credentials=True`.
- `db.md` P2-2 — `sa.JSON()` instead of PG `JSONB`.

P2s are typically bundled into a "hardening" PR alongside P1 work or deferred to a backlog file (e.g., `agent_docs/audits/<DATE>/DEFERRED.md`).

### P3 — Nice-to-have: defer

Aesthetics, ordering, micro-cleanups, speculative future work where the current state is already correct. Example: `claude-infra.md` P3-1 — "Don't" section duplicates content already covered upstream. **Always defer P3.** Listing it is enough; no fix scope.

### Calibration cross-checks

After drafting findings, before writing the report, sanity-check:

- **Does my P0 list pass the "would I bother Tim about this on a Sunday?" test?** If no, demote.
- **Are my P1s individually fixable in a sized PR?** If a P1 needs >1 week of work, split or demote.
- **Am I over-counting in one priority bucket?** A dimension with 0 P0 and 12 P1 is suspicious — likely 4 of those P1s are P2.
- **Does each finding cite a specific path:line?** No citation = no finding.

## Notable strengths section (mandatory)

Every report ends with **3–7 bullets of what's GOOD** in the audited surface. This is **not optional praise** — it serves three purposes:

1. **Anchors calibration.** "We have value objects defined" sets the bar against which "we have primitive obsession in TradeSignal" is a real problem.
2. **Prevents disturbance.** The next refactor PR can read the strengths list and avoid breaking exemplary patterns. Example from `architecture.md`: *"`PortfolioCalculator`, `SnapshotCalculator`, `trade_factory` are exemplary pure domain services — all functions static or take `timestamp` as a parameter, no I/O."*
3. **Counterweight to the negative tone of audit work.** The orchestrator and Tim need to know what's working too.

If you can't find 3 strengths in the surface you audited, audit harder — or the dimension scope is too narrow.

## Effort estimate

Include a per-priority effort estimate. Rough buckets used in 2026-05-09:

- **15 min** — one-line config / typo / single-file rename
- **30–60 min** — single-file fix with tests
- **2–3 h** — single-feature refactor across 3–6 files
- **1 day** — cross-cutting refactor or new test suite
- **>1 day** — too big; split

These let the orchestrator scope fix-waves accurately. They do not need to be precise; ranges (`~2–3h`) are fine.

## Reporting back to the orchestrator

After the report is written, reply to the orchestrator with **a tight summary, under ~150 words**:

- **File path** of the report
- **P-counts**: `P0: N / P1: N / P2: N / P3: N`
- **Top concern** in one sentence (mirror the report's "Top concern" line)
- **Anything urgent** the orchestrator should escalate immediately (e.g., a security P0 that should be hot-fixed before the rest of the audit even completes)
- **Anything worth queueing for a follow-up audit** that you couldn't reach in this scope

Example response:

> Wrote `agent_docs/audits/2026-05-09/architecture.md`. P0: 2 / P1: 5 / P2: 5 / P3: 2. Top concern: Domain imports from Application — strategy modules pull `PricePoint` from `application.dtos`, creating a real Domain↔Application cycle that every Phase C/F live executor will inherit. Effort: ~16–20h total to close P0+P1. No security urgencies. Worth queueing: a follow-up `mcp-conventions` audit once Phase D scope firms up.

## Multi-agent dispatch pattern (for the orchestrator)

When dispatching a full audit cycle (12 dimensions in 2026-05-09):

- **Parallelize.** Each dimension is independent on read-only inputs, so dispatch all of them in parallel specialist agents. The 2026-05-09 cycle ran 12 audits in parallel and consolidated.
- **Worktree isolation.** Each audit agent should run in its own git worktree so one agent's read state never sees another's drafts. (`git worktree add` per agent; the agent writes to `agent_docs/audits/<DATE>/<slug>.md` directly.)
- **One date, one cycle.** All audits in a cycle share a single `<YYYY-MM-DD>` directory. If a follow-up audit runs a week later, it gets its own dated directory.
- **Orchestrator writes SUMMARY.md.** After all per-dimension reports land, the orchestrator reads them, builds the P-count matrix (see `agent_docs/audits/2026-05-09/SUMMARY.md` for the table format), drafts an execution wave plan, and surfaces the consolidated finding set for Tim's signoff.
- **Audit cycle finishes with a wave plan**, not with code changes. Code changes happen in `Wave N — <theme>` PRs dispatched after the audit closes.

## Anti-patterns

- **Don't fix while auditing.** The temptation is real ("oh I can just change this one line"). Don't. Every fix during audit time is a fix that didn't go through review and isn't tracked in the wave plan. Fixes are separate PRs.
- **Don't stop at "I found a problem."** A finding without a citation, an effort estimate, or a recommended fix is not actionable. The orchestrator can't dispatch a fix from "the database layer feels wrong."
- **Don't audit the agent files inside an agent file's audit.** When `architect` is auditing the `claude-infra` dimension, `architect.md` is a valid target — just be explicit about the recursion in the report scope so a future reader knows.
- **Don't over-cite.** Three exemplary citations per finding is plenty. Don't list every occurrence of a pattern; one or two and a "(plus N more)" is enough.
- **Don't pad with P3.** P3 is for things you noticed but explicitly defer. If you have 8 P3s, half of them are probably noise.

## See also

- `agent_docs/audits/2026-05-09/SUMMARY.md` — the consolidator that demonstrates wave planning
- `agent_docs/audits/2026-05-09/claude-infra.md` — the report that surfaced the gap this skill closes (GAP-1)
- `docs/planning/agent-platform-proposal.md` §B1 — the proposal scope that defined the 12 dimensions
- `.claude/skills/orchestrate-zebu/SKILL.md` — orchestration rules for parallel multi-agent dispatch
- `.claude/skills/before-starting-work/SKILL.md` — the implementation-mode equivalent of audit mode's pre-work
