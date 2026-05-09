# Claude Infra Sync — 2026-05-09

- **Run by**: orchestrator subagent (Wave 5-C dispatch)
- **Trigger**: end-of-Phase-B / Wave 5-C closeout (first run since the skill shipped in PR #230)
- **Scope**: `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`
- **Snapshot**: 7 agents, 8 skills, **2,193** total lines of Claude infra (including this skill's own 357 lines)

## Summary

| Severity | Count |
|---|---:|
| BLOCKER | 2 |
| WARN | 4 |
| NIT | 3 |
| **Total** | **9** |

**Top concern (one sentence)**: `backend/pyproject.toml` declares `requires-python = ">=3.12"` while `CLAUDE.md`, `backend-swe.md`, and CI (`ci.yml`, `docs.yml`, `copilot-setup-steps.yml`) all specify Python 3.13 — a contradiction that will silently let a 3.12 environment install dependencies that the agent files (and CI) assume require 3.13.

The repo is healthier than the 2026-05-09 audit's 14 findings (3 P0 / 5 P1 / 4 P2 / 2 P3) — most P0/P1 items there have been addressed by PRs #217, #229, #230. Remaining drift is concentrated in (a) version pin slipping out of sync with claims and (b) terminology / pointer cleanup that didn't make the earlier waves.

---

## BLOCKER

### [BLOCKER-1] Python version drift: `backend/pyproject.toml` says >=3.12, everything else says 3.13

- **Where**:
  - `backend/pyproject.toml:10` — `requires-python = ">=3.12"`
  - `CLAUDE.md:7` — `**Backend** — Python 3.13+, FastAPI, …`
  - `.claude/agents/backend-swe.md:12` — `Python 3.13+, FastAPI, SQLModel, …`
  - `.github/workflows/ci.yml:77,203` — `python-version: '3.13'`
  - `.github/workflows/docs.yml:32` — `python-version: '3.13'`
  - `.github/workflows/copilot-setup-steps.yml:50` — `python-version: '3.13'  # Match pyproject.toml requirements (3.13+)` (the comment itself contradicts the actual pin)
- **Drift**: pyproject says `>=3.12`; agent files, CLAUDE.md, and three CI workflows all say `3.13`; the `copilot-setup-steps.yml` comment even claims pyproject is "3.13+" when it isn't.
- **Why it matters**: If a developer (or agent) installs the project with Python 3.12 because pyproject allows it, they'll diverge from the documented + CI floor and may hit subtle Python-3.13-only behavior (e.g. type-system features, stdlib changes) without warning. CI will pass on 3.13; local will silently sit on 3.12. The agent file claim is also load-bearing for `backend-swe` decisions about what Python features to use.
- **Suggested fix**: Bump `backend/pyproject.toml:10` to `requires-python = ">=3.13"` (CI already mandates 3.13, so no environment regression). The agent files are correct; pyproject is the outlier. Update the (now-outdated) comment in `copilot-setup-steps.yml:50` to drop the now-redundant clarifier.

### [BLOCKER-2] `backend/docs/SCHEDULER.md` still links to `architecture_plans/` — the directory deleted in PR #217

- **Where**:
  - `backend/docs/SCHEDULER.md:100` — `[ADR 003: Background Refresh Strategy](../../architecture_plans/20251228_phase2-market-data/adr-003-background-refresh.md)`
  - `backend/docs/SCHEDULER.md:101` — `[Market Data Architecture](../../architecture_plans/20251228_phase2-market-data/overview.md)`
- **Drift**: `architecture_plans/` was the canonical drift case from the 2026-05-09 audit (`CLAUDE-P0-1`). PR #217 removed the directory and updated `CLAUDE.md`, `architect.md`, `backend-swe.md`, and `before-starting-work/SKILL.md`. It missed `backend/docs/SCHEDULER.md`, which still has two dangling markdown links.
- **Why it matters**: The two link targets actually exist at `docs/architecture/archived/20251228_phase2-market-data/{adr-003-background-refresh.md,overview.md}` — but the relative paths from `backend/docs/SCHEDULER.md` point at the deleted directory. Anyone clicking these links from the rendered docs site (or an agent following them) gets a 404. This is a finish-the-cleanup item from PR #217.
- **Suggested fix**: Update both lines to point at `../../docs/architecture/archived/20251228_phase2-market-data/...` (relative path from `backend/docs/`). Verified targets exist.

---

## WARN

### [WARN-1] Terminology drift: 4 variants of "agent" in active use across `CLAUDE.md` + `.claude/`

- **Where** (excluding the `claude-infra-sync` skill's own enumeration list, which is not in active use):
  - `specialist agent(s)`: 5 occurrences — `CLAUDE.md:59`, `.claude/skills/audit-mode/SKILL.md:3,8,12`, `.claude/skills/orchestrate-zebu/SKILL.md:8`
  - `subagent`: 1 occurrence — `CLAUDE.md:64` (`subagent_type` — literal API parameter name, **cannot be changed**)
  - `sub-agent`: 2 occurrences — `.claude/skills/audit-mode/SKILL.md:223`, `.claude/skills/orchestrate-zebu/SKILL.md:82`
  - `specialist-agent` (hyphenated, no space): 0 occurrences in active use (only in the skill's own term-counter loop)
- **Drift**: `CLAUDE.md` heading is `## Specialist agents` (line 62), but two skills say `sub-agent` for the same concept. The `subagent_type` literal at `CLAUDE.md:64` is fine — it's the actual API parameter name passed to the `Agent` tool, so it's not a candidate for renaming.
- **Why it matters**: Mostly cosmetic, but a future agent loading multiple skills sees `specialist agent` and `sub-agent` referring to the same thing without a connecting definition. Compounds confusion as more skills land.
- **Suggested fix**: Rewrite the 2 `sub-agent` instances to `specialist agent` (matches the `CLAUDE.md` heading and is the most-used variant). Leave `subagent_type` alone — it's the literal API param.

### [WARN-2] `architect.md` schema lists 3 paths that don't exist under `docs/architecture/`

- **Where**:
  - `.claude/agents/architect.md:24` — `decisions/NNN-title.md    # ADRs`
  - `.claude/agents/architect.md:26` — `domain/{entities,value-objects,services}.md`
  - `.claude/agents/architect.md:27` — `api/contracts.md          # OpenAPI specs`
  - `.claude/agents/architect.md:99` — `add an ADR under \`docs/architecture/decisions/NNN-title.md\``
  - `.claude/agents/frontend-swe.md:20` — `\`docs/architecture/api/\` for backend contracts when integrating`
- **Drift**: Real `docs/architecture/` contents: `archived/`, `authentication.md`, `phase4-trading-strategies.md`, `principles.md`, `README.md`, `technical-boundaries.md`. None of `decisions/`, `domain/`, `api/` exist.
- **Why it matters**: An architect dispatched today will follow line 99 and try to write to `docs/architecture/decisions/NNN-title.md` in a directory that doesn't exist (the parent `docs/architecture/` does, so the write will succeed without `mkdir -p`, but the agent has no way to know whether that's the right place — there's no precedent file to mirror). A frontend-swe will run `ls docs/architecture/api/` per line 20 and find nothing.
- **Suggested fix**: Two options — either (a) treat `architect.md`'s schema block as **target / aspirational** and add a note on line 21 like "(some subdirs are created on first write)", or (b) trim the schema block to only list paths that exist today. Option (a) is lower-risk; the schema documents an intended convention. For the `frontend-swe.md:20` bullet — drop the `docs/architecture/api/` reference (no contracts file exists yet); keep only `frontend/package.json` and `frontend/src/components/` bullets, both of which exist.

### [WARN-3] Audit example date in `claude-infra-sync` skill's own example response is 2026-06-15

- **Where**: `.claude/skills/claude-infra-sync/SKILL.md:338` — example response uses `agent_docs/sync-checks/2026-06-15/REPORT.md`
- **Drift**: The example sync date in the skill is 5 weeks in the future. False positive against this skill's own Pass 1 (the helper script picked it up as a missing path).
- **Why it matters**: Cosmetic — but the helper script will keep flagging this on every run. Either filter it (it's an example) or pick a date that's already in the past.
- **Suggested fix**: Change `2026-06-15` to `2026-05-09` (today, matching the actual first dispatch).

### [WARN-4] `agent_docs/audits/2026-05-09/SUMMARY.md` Wave plan implies Wave 2-A is "create architecture_plans/" but PR #217 deleted the concept entirely

- **Where**: `agent_docs/audits/2026-05-09/SUMMARY.md:90` — `| W2-A | \`fix(claude-infra): create architecture_plans/, fix CLAUDE.md inconsistencies, drop stale Copilot refs in agent files\` | \`claude.P0-1\`, \`claude.P0-2\`, \`claude.P0-3\` |`
- **Drift**: The SUMMARY description says "create architecture_plans/" but PR #217 (which closed Wave 2-A) **deleted** the architecture_plans concept entirely. The decision changed from the plan; the SUMMARY still records the original intent.
- **Why it matters**: A future reader skimming the SUMMARY for Wave plans will see a contradiction with what shipped. Compounds if the SUMMARY is referenced by future audits as "what got done."
- **Disposition**: **Deferred — historical record.** `agent_docs/audits/` is an immutable record per `audit-mode` skill convention; editing a past SUMMARY rewrites history. The Wave label / PR citation is accurate; only the planned-vs-shipped scope diverges. Listed as WARN (don't fix in scope); call out for awareness.

---

## NIT

### [NIT-1] `docs-refactorer.md:15` mentions `Last Updated` headers as a freshness signal — no such convention exists in the repo

- **Where**: `.claude/agents/docs-refactorer.md:15` — `**Freshness** — \`Last Updated\` headers, git timestamps.`
- **Drift**: `grep -rn "Last Updated" docs/ agent_docs/ .claude/ | wc -l` returns very few hits (mostly archive content). Convention isn't real.
- **Why it matters**: Misleads the docs-refactorer to look for a signal that mostly isn't there. Already flagged as `CLAUDE-P2-4` in the 2026-05-09 audit; deferred until B6.
- **Suggested fix**: Either drop the line or commit to the convention. Defer per audit recommendation.

### [NIT-2] `before-starting-work` skill is borderline always-on

- **Where**: `.claude/skills/before-starting-work/SKILL.md` (entire file, 71 lines)
- **Drift**: Already flagged as `CLAUDE-P2-2` in the 2026-05-09 audit. Not actively breaking.
- **Suggested fix**: Defer to a future P3 cleanup pass.

### [NIT-3] Agent frontmatter `description` strings are uniformly long

- **Where**: All `.claude/agents/*.md` frontmatter `description:` fields.
- **Drift**: Already flagged as `CLAUDE-P3-2` in the 2026-05-09 audit.
- **Suggested fix**: Defer.

---

## Inventory snapshot

| Surface | Count | Notes |
|---|---:|---|
| Agents (`.claude/agents/`) | 7 | architect, backend-swe, docs-refactorer, frontend-swe, qa, quality-infra, refactorer |
| Skills (`.claude/skills/`) | 8 | audit-mode, before-starting-work, claude-infra-sync, docs-tidy, e2e-qa-validation, git-workflow, orchestrate-zebu, quality-checks |
| `CLAUDE.md` lines | 116 | |
| Total Claude infra lines | 2,193 | including the 357-line `claude-infra-sync/SKILL.md` itself |
| Most recent task | `210_live_strategy_execution.md` | "next is 211" agrees in `CLAUDE.md`, `agent_docs/README.md`, `before-starting-work/SKILL.md` |

### Inventory passes (Pass 3 / Pass 4)

Both clean — every skill listed in CLAUDE.md exists on disk; every agent listed exists; no orphans.

### Test counts (Pass 5)

`README.md` (831 backend / 311 frontend / 1,142 total) agrees with `PROGRESS.md:393` Key Metrics row exactly. Other PROGRESS.md numbers (262, 796, 402) are historical milestone records, correct as written.

### Endpoint references (Pass 7)

No `/api/v1/...` literals in `.claude/agents/` or `CLAUDE.md`. Pass skipped as N/A.

### Removed concepts (Pass 8)

Concepts referenced in agent files (`InsufficientFundsError`, `InvalidTradeError`, `Money`, `Portfolio`, `ExplorationTask`) all either exist in code or are explicitly forward-looking (e.g. `ExplorationTask` is queued for Phase B per `CLAUDE.md:99`). No false-orphan findings.

---

## Deferred (cannot fix in this PR scope)

| Item | Severity | Reason | Effort |
|---|---|---|---|
| WARN-4 — SUMMARY.md Wave 2-A description | WARN | `agent_docs/audits/` is an immutable historical record per `audit-mode` skill convention. | n/a (don't fix) |
| NIT-1 — `Last Updated` convention | NIT | Decision item: adopt the convention or drop it. Out of scope for a drift-fix Wave. | 30 min |
| NIT-2 — `before-starting-work` always-on | NIT | Restructuring CLAUDE.md is feature work, not drift cleanup. | 1–2 h |
| NIT-3 — Frontmatter descriptions length | NIT | Editorial / cosmetic. Defer to docs-tidy. | 1 h |

---

## Recommended follow-up

- **BLOCKERs (this PR)**: bump `backend/pyproject.toml` to 3.13; fix the two `architecture_plans/` links in `backend/docs/SCHEDULER.md`. Run `task quality:backend` and backend tests since pyproject changed. Update the now-stale comment in `copilot-setup-steps.yml:50`.
- **WARN-1 (this PR)**: rewrite 2 `sub-agent` instances to `specialist agent`.
- **WARN-2 (this PR)**: add a "some subdirs created on first write" note to `architect.md:21`; drop the `docs/architecture/api/` bullet from `frontend-swe.md:20`.
- **WARN-3 (this PR)**: change `2026-06-15` example date in `claude-infra-sync/SKILL.md:338` to `2026-05-09`.
- **WARN-4 (deferred)**: leave `agent_docs/audits/2026-05-09/SUMMARY.md` as historical record.
- **NIT-1, NIT-2, NIT-3 (deferred)**: queue for next docs-tidy pass.

---

## What this run did NOT cover

- **Live test-count grounding**: didn't run `task quality:backend` / `quality:frontend` to verify the 1,142 number is current. PROGRESS.md is authoritative per skill convention.
- **Pyright / ESLint code-pattern freshness**: skipped Pass 5 sub-bullet from `CLAUDE-P1-2` ("sample one file from each agent's domain and check that the code snippets in the agent file would still pass current Pyright/ESLint config"). Out of scope this run.
- **Phase D MCP gap**: 2026-05-09 audit's `CLAUDE-P1-5` recommended an `mcp-builder` agent or `mcp-conventions` skill; still not present. Deferred to Phase D scope landing.
