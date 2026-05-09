# Claude Infrastructure Audit — Phase B1

- **Auditors**: `architect` + `docs-refactorer` (audit mode)
- **Slug**: `claude`
- **Date**: 2026-05-09
- **Scope**: `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`
- **Source files reviewed**:
  - `CLAUDE.md` (113 lines)
  - `.claude/agents/architect.md`, `backend-swe.md`, `frontend-swe.md`, `qa.md`, `quality-infra.md`, `refactorer.md`, `docs-refactorer.md`
  - `.claude/skills/before-starting-work/SKILL.md`, `quality-checks/SKILL.md`, `git-workflow/SKILL.md`, `e2e-qa-validation/SKILL.md`, `docs-tidy/SKILL.md`, `orchestrate-zebu/SKILL.md`
  - Cross-checked against `agent_docs/README.md`, `docs/architecture/`, `frontend/package.json`, `frontend/src/**/*.tsx`, `docs/planning/agent-platform-proposal.md` §B7

## Summary

| P | Count |
|---|------:|
| P0 | 3 |
| P1 | 5 |
| P2 | 4 |
| P3 | 2 |

**Top concern (single sentence):** Three agent files (`architect`, `backend-swe`) plus the `before-starting-work` skill direct agents to write into / read from `architecture_plans/` — **a directory that does not exist in this repo**. Any `architect` invocation today will silently produce orphan files in a path the rest of the toolchain doesn't know about, and any `backend-swe` invocation that tries to follow a plan there will get nothing. This is a P0 contradiction baked into the migration.

**Top GAP-skill recommendation for B7:**

1. **`claude-infra-sync` (already named in the proposal)** — this audit produced its concrete spec. See `CLAUDE-P1-2` below for the checks it should run.
2. **`audit-mode` (new) + per-agent "Audit mode" frontmatter section** — `B1` tables in the proposal repeatedly say "`backend-swe` (audit mode)", "`frontend-swe` (audit mode)", "`docs-refactorer` (audit mode)" — but no agent file mentions audit mode, no skill defines it, and the actual prompt I (this auditor) had to be given was hand-rolled. Without codifying it, every future audit cycle (B1 won't be the last) re-invents the rubric. See `CLAUDE-P0-3`.

The remainder of the report is the prioritized findings.

---

## P0 — Contradictions / stale references that will actively mislead a future agent

### CLAUDE-P0-1 — `architecture_plans/` is referenced as a real directory but doesn't exist

**Files**:

- `.claude/agents/architect.md` lines 28–38 — instructs the architect to write per-feature plans into `architecture_plans/YYYYMMDD_feature-name/`
- `.claude/agents/backend-swe.md` line 20 — `If a plan exists in architecture_plans/, implement it as written`
- `.claude/skills/before-starting-work/SKILL.md` line 31 — `ls -la architecture_plans/      # if it exists`
- `.claude/skills/before-starting-work/SKILL.md` line 32 — `If a plan exists for the feature you're working on, implement it as written`

**Evidence**: `ls /Users/timchild/github/PaperTrade/architecture_plans/` → `No such file or directory`. The path is **not** in `agent_docs/README.md`'s structure either. Recent work uses `agent_docs/tasks/NNN_*.md` exclusively (e.g. `200_phase4_architecture_design.md`, `200b_phase4_architecture_design_v2.md`) — those files are doing the job `architecture_plans/` was meant to do, but under a different name.

**Impact**: An `architect` invocation today will create a brand-new `architecture_plans/` tree that diverges from the established `agent_docs/tasks/` convention, producing two separate "where the design lives" locations. The `backend-swe` agent reading "if a plan exists in `architecture_plans/`" will conclude no plan exists when a perfectly good one is sitting in `agent_docs/tasks/`.

**Fix (B7)**: Pick one. Recommendation: **delete the `architecture_plans/` concept entirely** and standardize on `agent_docs/tasks/NNN_*.md` for both task specs and per-feature design docs (the existing `200*_phase4_architecture_design.md` files prove this works). Update:

- `architect.md` "Output locations" — replace the `architecture_plans/...` block with `docs/architecture/decisions/NNN-title.md` for ADRs and `agent_docs/tasks/NNN_short_name.md` for per-feature design specs (mirroring what's already in CLAUDE.md's "Task workflow" section).
- `backend-swe.md` line 20 — change to `If a task spec exists at agent_docs/tasks/NNN_*.md, implement it as written`.
- `before-starting-work/SKILL.md` lines 30–32 — drop the `architecture_plans/` line; the `agent_docs/tasks/` mention on line 54 is sufficient.

### CLAUDE-P0-2 — CLAUDE.md says "Phase 5" while the active proposal says "Phases A–F"

**File**: `CLAUDE.md` line 3

> See `docs/planning/agent-platform-proposal.md` for the active forward plan (agent-driven trading, **Phase 5**).

But `CLAUDE.md` line 95 (correctly) says "**six phases (A–F)**" and `CLAUDE.md` line 97 says "Phase A (this Claude infra migration) is in progress as of 2026-05-09. **Phase B**...". The proposal itself (`agent-platform-proposal.md` line 6) literally **supersedes** the old "Phase 5" naming: `**Supersedes**: roadmap.md § "Phase 5: Automation & Advanced Analytics" (loose sketch)`.

**Impact**: A new agent reading the first paragraph of CLAUDE.md will internalize "Phase 5" as the project state, which contradicts the rest of the same file *and* the proposal it points to. This is exactly the class of drift the audit was meant to catch.

**Fix (B7)**: One-line edit on `CLAUDE.md:3` — `(agent-driven trading, Phases A–F)` or simpler `(agent-driven trading; Phase A done, Phase B in progress)`.

### CLAUDE-P0-3 — "Audit mode" is a load-bearing concept in the proposal but is undefined anywhere in `.claude/`

**Files**:

- `docs/planning/agent-platform-proposal.md` lines 170, 171, 180 — repeatedly invokes `backend-swe (audit mode)`, `frontend-swe (audit mode)`, `architect + docs-refactorer (audit mode)`
- `.claude/agents/*.md` — **no agent file mentions audit mode**
- `.claude/skills/*/SKILL.md` — **no skill defines audit mode**

**Evidence**: `grep -n "audit mode" .claude/` → empty.

**Impact**: When the orchestrator dispatches an `audit mode` instance of `backend-swe`, it has no shared definition of what that means, so each subagent inherits a hand-crafted prompt (as I did for this audit). For B1 with 12 parallel auditors this is tolerable; for B-style cycles repeating across Phases C–G, it's a P0 gap because:

1. Each audit has to re-bootstrap the "no code changes, only findings", "P0/P1/P2/P3 calibration", "report at `agent_docs/audits/YYYY-MM-DD/<slug>.md`" rubric.
2. Without a shared rubric, auditor outputs will drift in shape — making `SUMMARY.md` consolidation harder for the orchestrator each cycle.

**Fix (B7)**: Two complementary changes —

- **(a)** Add a section `## Audit mode` (or top-level `### Mode: audit` flag in frontmatter) to each agent file. Body: "produces a report at `agent_docs/audits/YYYY-MM-DD/<slug>.md`, never edits source files, calibrates findings as P0/P1/P2/P3 (definitions inline), 5–15 findings".
- **(b)** Promote the shared rubric (output path convention, P-tier definitions, summary table format) to a new skill `.claude/skills/audit-mode/SKILL.md`. Each agent's audit-mode section then becomes 3 lines that point at the skill.

This skill is **distinct from `claude-infra-sync`** and is at least as load-bearing for Phase B–G cadence.

---

## P1 — Missing-but-needed structure / agent definitions vague enough that role-selection gets confused

### CLAUDE-P1-1 — `architect` and `refactorer` overlap awkwardly, with no decision rule

**Files**: `.claude/agents/architect.md` lines 109–121; `.claude/agents/refactorer.md` lines 19–25, 119–126

`architect.md` "When to engage" includes:

- "New cross-layer feature requiring port design"
- "ADRs when a non-obvious architectural choice is being made"

`refactorer.md` "When to engage" includes:

- "Architecture boundaries are blurred"
- "Before adding features to complex code"

Both can plausibly handle the question *"Should this become a port?"* applied to existing code. `architect.md` "Out of scope" line 119 says `Refactoring decisions on already-implemented code (delegate to refactorer)` — but `refactorer.md` "Out of scope" line 130 says `Architecture redesign (delegate to architect)`. So **structural changes to existing-code architecture have no clear owner**: each delegates to the other.

**Impact**: For Phase B3 (foundation refactors based on B1 findings), the orchestrator needs to know whether `Domain entity X has a value-object opportunity` is `architect` work (declares the new VO) or `refactorer` work (does the substitution). Today the answer is ambiguous, so the orchestrator may pick wrong, or end up dispatching both in series and paying double.

**Fix (B7)**: Make the rule explicit in both files. Suggested: "**`architect` decides the target shape; `refactorer` performs the substitution.** If existing code needs to become a new design, dispatch `architect` first to write the spec (output to `agent_docs/tasks/NNN_*.md`), then `refactorer` to apply it (under the spec's reference)." This codifies the actual current pattern from `200_phase4_architecture_design.md` → implementation tasks.

### CLAUDE-P1-2 — `claude-infra-sync` is mentioned in §B7 but the audit had no place to record gap-skill suggestions; the spec needs to be concrete

The proposal §B7 says the sync skill should detect "stale paths, broken file references, outdated test counts, removed endpoints, agent definitions referencing concepts that no longer exist, suggest skill candidates from observed patterns". This audit confirms that scope is correct and produced live evidence of what each check would catch:

- **Stale paths**: `architecture_plans/` (CLAUDE-P0-1)
- **Drift in version claims**: "Phase 5" vs "Phases A–F" (CLAUDE-P0-2), "React 18+" vs actual `^19.2.0` (CLAUDE-P1-3)
- **Unreferenced concepts**: "audit mode" mentioned in proposal but undefined in `.claude/` (CLAUDE-P0-3)
- **Type-checker stale examples**: `JSX.Element` in `frontend-swe.md` vs `React.JSX.Element` in actual code (CLAUDE-P1-3)
- **Numeric drift**: `next number is 211` in three places (CLAUDE.md, `before-starting-work`, `agent_docs/README.md`) — three sources of truth for the same fact (CLAUDE-P2-1)
- **Skill ↔ CLAUDE.md inventory mismatch**: this audit caught none today, but the sync skill should run `diff <(ls .claude/skills/) <(grep skill-rows-in-CLAUDE.md)` as a routine check.

**Concrete fix (B7)**: ship `.claude/skills/claude-infra-sync/SKILL.md` with sections:

1. **Stale-path scan** — `grep -rE "agent_docs/|backend/src/|docs/" .claude/ CLAUDE.md` then verify each match exists; emit warnings.
2. **Concept ↔ definition diff** — `grep -oE "audit mode|architect|refactorer|..." docs/planning/*.md | sort -u` cross-referenced against agent files; flag concepts that appear in plans but not in agent definitions.
3. **Inventory drift** — every agent named in CLAUDE.md must exist in `.claude/agents/`; every skill named must exist in `.claude/skills/`; vice-versa.
4. **Single-source-of-truth check** — fact "next task number" appears in CLAUDE.md, before-starting-work, and `agent_docs/README.md`. Require these to agree (or move to a single source).
5. **Code-pattern freshness** — sample one file from each agent's domain and check that the code snippets in the agent file would still pass current Pyright/ESLint config.

Output: a markdown findings doc the user/`docs-refactorer` runs through. Schedule: end of every major phase.

### CLAUDE-P1-3 — `frontend-swe.md` examples are stale against React 19 / current code

**Files**: `.claude/agents/frontend-swe.md` lines 12, 62

**Evidence**:

- `frontend-swe.md` line 12: `TypeScript (strict), React 18+, Vite, ...` — but `frontend/package.json` line 35 has `"react": "^19.2.0"`.
- `frontend-swe.md` line 62 example: `}: PortfolioCardProps): JSX.Element {` — but **every actual production component** in `frontend/src/` uses `React.JSX.Element` (verified across 10+ files: `ThemeContext.tsx:25`, `ConfirmDialog.tsx:26`, `PriceStats.tsx:18`, `theme-toggle.tsx:11`, `PriceChartError.tsx:16,69`, `ComparisonChart.tsx:41`, `ErrorState.tsx:22`, `TimeRangeSelector.tsx:16`, `LightweightPriceChart.tsx:63`).

**Impact**: A `frontend-swe` instance that follows the agent file literally will introduce a `JSX.Element` import / type that will *probably* still typecheck in React 19 (the global `JSX` namespace was removed in React 19's main types but is sometimes re-added by `@types/react`), and at minimum will be **inconsistent** with the rest of the codebase. Project pride is "0 ESLint suppressions" — having the agent file diverge from real code is the first crack.

**Fix (B7)**:

- `frontend-swe.md` line 12: replace `React 18+` with `React 19+`.
- `frontend-swe.md` lines 51–73 example: change `JSX.Element` → `React.JSX.Element` (and import note: `import * as React from 'react'` or `import type { JSX } from 'react'` per current `@types/react` behavior — pick the one matching the actual `tsconfig.json` / `vite.config.ts`).

### CLAUDE-P1-4 — `qa.md` is thin; most of the testable content lives in `e2e-qa-validation` skill, but the agent file duplicates ~half of it

**Files**: `.claude/agents/qa.md` (90 lines) vs `.claude/skills/e2e-qa-validation/SKILL.md` (164 lines)

**Evidence**: Both define the severity rubric (`qa.md` lines 30–37 ≈ `e2e-qa-validation` lines 105–110). Both define the report template (`qa.md` lines 40–66 ≈ `e2e-qa-validation` lines 116–143). Both have a "When to run" / "When to engage" list with overlapping bullets. The `qa.md` workflow (lines 72–78) is a 5-step compressed version of the skill's full procedure.

**Impact**: When the agent file and the skill drift (which they will), an agent loaded with both has to pick. In practice the skill will get updated more (it's longer, more procedural), the agent file will rot, and dispatching `qa` will produce subtly stale reports.

**Fix (B7)**: Make `qa.md` short — frontmatter + ~30 lines: "When to engage", "Out of scope", and a single load-bearing line: `For the test plan, severity rubric, and report template, run the e2e-qa-validation skill`. Move the duplicated rubric/template entirely to the skill. This is the same model as `qa.md:27` already does for the 7 scenarios — extend it to severity + report.

### CLAUDE-P1-5 — There's no agent or skill for the work coming in Phase D (MCP server build) — `mcp-builder` is a clean gap

**Files**: `docs/planning/agent-platform-proposal.md` §D (referenced at lines 294, 312); `agent_docs/mcp-tools.md` (exists but is a dev tooling reference, not an agent definition)

**Evidence**: Phase D in the proposal is "MCP server" work. The mcp-builder skill from the user's marketplace (`internal-apps:build-mcp-server`) handles MCP scaffolding for **Exowatt internal apps** (i.e. `*.apps.exowatt.com`), not for an agent-platform-style MCP attached to Zebu. There's no `mcp-builder` agent or skill in `.claude/agents/` or `.claude/skills/`, and no Zebu-specific MCP-implementation conventions captured anywhere.

**Impact**: When Phase D starts, the orchestrator will dispatch `backend-swe` to do MCP work that has fundamentally different conventions (tool naming, schema design, transport, auth carriage) than REST API work. `backend-swe.md` has no MCP guidance. The agent will invent conventions ad-hoc, and a B-style audit two phases later will catch the resulting drift.

**Fix (B7)** *(speculative — depends on Phase D scope landing)*: Either

- Add a Phase D-specific agent `.claude/agents/mcp-builder.md` (Zebu-tuned: tool-name conventions, schema patterns for read-only vs write, where in `adapters/inbound/` an MCP surface lives, auth/JWT-bearer carriage, integration with the API-key path being added in Phase B/C), or
- Add a `.claude/skills/mcp-conventions/SKILL.md` and have `backend-swe` reference it under "When to engage → MCP endpoints".

The agent option is cleaner if MCP work is going to be 3+ tasks; the skill is enough if it's a one-shot.

---

## P2 — Tightening / merging / splitting opportunities

### CLAUDE-P2-1 — "Next task number is 211" is hardcoded in three places

**Files**: `CLAUDE.md` line 89; `agent_docs/README.md` line 24; `.claude/skills/before-starting-work/SKILL.md` line 54

All three say "the next number is **211** — most recent is `210_live_strategy_execution.md`". The day Task 211 lands, all three drift in lockstep until someone notices.

**Fix (B7)**: Pick one home. Recommendation: keep it in `agent_docs/README.md` (the canonical "what is this directory" doc) and replace the other two with "see `agent_docs/README.md` for the next task number". Better: drop the hardcoded number entirely from all three; replace with a one-liner `ls agent_docs/tasks/ | grep -E '^[0-9]' | sort -n | tail -1` in `before-starting-work`. The number itself isn't useful without verifying the most-recent-task; a command beats a stale hardcode.

### CLAUDE-P2-2 — Skill granularity: `before-starting-work` is borderline always-on

**File**: `.claude/skills/before-starting-work/SKILL.md` (71 lines)

Most of this skill's content (recent agent activity, open PRs, current code state, project context) is what every non-trivial task should do. It's a checklist, not a procedure. A future audit might profitably either:

- **Promote** the 4-step quick-start one-liner (`SKILL.md` lines 58–63) into CLAUDE.md as an always-on context block, **or**
- **Demote** the rest of the skill content into smaller targeted skills (e.g. `pr-coordination`, `recent-work-context`).

Today's friction is small; flagging now because future agents will load this skill on essentially every session, which is what CLAUDE.md is for.

### CLAUDE-P2-3 — Inconsistent terminology: "specialist agents" / "subagents" / "agents" / "sub-agent"

**Files**:

- `CLAUDE.md` line 62: `## Specialist agents`
- `CLAUDE.md` line 64: `Use the Agent tool with the matching subagent_type`
- `agent_docs/README.md` line 12: `Specialist agent definitions`
- `.claude/skills/orchestrate-zebu/SKILL.md` line 8: `specialist agents`
- `.claude/skills/orchestrate-zebu/SKILL.md` line 82: `local sub-agent`

**Fix (B7)**: Adopt one term — "specialist agents" is the most informative and matches existing usage 4/5 places. Replace `subagent_type` (which is the literal API parameter) and `sub-agent` (line 82) with consistent language. Rename `Use the Agent tool with the matching subagent_type` to `Use the Task tool with the matching agent type` — *the actual underlying tool name in Claude Code is `Task`, not `Agent`* (verify against the harness; if I'm wrong here it's still worth confirming).

### CLAUDE-P2-4 — `docs-refactorer.md` references `Last Updated` headers as a freshness signal but no convention exists for them

**File**: `.claude/agents/docs-refactorer.md` line 15

> **Freshness** — `Last Updated` headers, git timestamps. PROGRESS.md is the source of truth for project state.

`grep -rn "Last Updated" docs/ agent_docs/` would tell us whether this is actually a convention. If most docs don't carry the header, this is either a discovery prompt that's misleading the agent (wasted scan) or a convention that should be enforced.

**Fix (B7)**: When tackling docs in B6, decide: either add `Last Updated:` headers as a convention (and update `docs-refactorer.md` to enforce it), or drop the line entirely and rely on git timestamps. Don't leave a half-cited convention.

---

## P3 — Aesthetics / ordering

### CLAUDE-P3-1 — `CLAUDE.md` "Don't" section duplicates content already covered upstream

**File**: `CLAUDE.md` lines 107–113

Three of five "Don't" bullets restate things already in §"Code quality bar" (no Any/any) or §"How to run things" (don't push without checks). The signal-bearing one is `Don't add a useEffect to sync props to state` because that's a project-specific anti-pattern that doesn't exist anywhere in CLAUDE.md outside this list.

**Fix (B7)**: Trim "Don't" to 2–3 unique bullets (the `useEffect` one, the `git add -A` one). Move the rest's content into the upstream sections they belong to.

### CLAUDE-P3-2 — Frontmatter `description` strings are uniformly long; could be tightened to make role-selection faster

**Files**: All 7 agents

Example: `architect.md` description is 25 words. The orchestrator selecting between agents reads these descriptions back-to-back. Aim for ~15 words each, leading with the action verb + the unique discriminator (e.g. `architect`: "Designs interfaces & specs (no code)"; `refactorer`: "Improves structure (preserves behavior)"). Keep the longer prose in the agent body.

---

## Cross-cutting observations

- **Migration was clean of Copilot residue.** `grep -rn "\.github/copilot|\.github/agents|agent_docs/reusable|orchestration-guide|copilot" .claude/ CLAUDE.md` returned **zero** matches. The verbatim-ish migration did successfully remove all old paths. (Phase A worked.)
- **No skills were lost in migration** — the skill names (`before-starting-work`, `quality-checks`, etc.) match the inventory in CLAUDE.md exactly.
- **The CLAUDE.md "Where things live" table** (lines 47–60) is accurate against the filesystem (verified `backend/src/zebu/domain/`, `application/services/backtest_executor.py`, etc. all exist).
- **Volume**: total Claude infra is **1,576 lines** across 14 files. `frontend-swe.md` (182 lines) and `e2e-qa-validation/SKILL.md` (164 lines) are the heaviest; both have duplication candidates flagged above.

---

## Recommended ordering for B7 fixes

If B7 is going to ship in priority order:

1. **CLAUDE-P0-1, CLAUDE-P0-2, CLAUDE-P0-3** — fix contradictions / undefined concepts. Cheap (mostly one-line edits + one new audit-mode skill).
2. **CLAUDE-P1-2** (`claude-infra-sync` skill) — ship next so subsequent audit cycles don't have to re-derive checks.
3. **CLAUDE-P1-1** (architect/refactorer rule), **CLAUDE-P1-3** (React 19), **CLAUDE-P1-4** (qa duplication trim) — small, valuable, decoupled.
4. **CLAUDE-P1-5** (mcp-builder) — defer until Phase D scope is firmer.
5. **P2/P3** — opportunistic.

The two highest-leverage B7 deliverables are the **`audit-mode` skill** (every Phase B audit cycle compounds value from it) and the **`claude-infra-sync` skill** (long-term insurance against this exact audit running again from scratch in Phase F).
