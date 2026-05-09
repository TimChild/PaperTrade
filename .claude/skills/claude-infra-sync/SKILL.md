---
name: claude-infra-sync
description: Detect drift between Claude infrastructure (CLAUDE.md, .claude/agents/, .claude/skills/) and the actual repo state. Produces a prioritized findings report at agent_docs/sync-checks/YYYY-MM-DD/REPORT.md citing stale paths, broken cross-links, outdated test counts, version drift, removed endpoints, missing/orphaned skills, and inconsistent terminology. Run on demand or at the end of every major Phase / Wave. Surfaces drift only — never auto-fixes.
---

# Claude Infra Sync

Lints the project's Claude-facing infrastructure — `CLAUDE.md`, every file under `.claude/agents/`, every `.claude/skills/*/SKILL.md` — against the actual repo. Catches the drift class that the 2026-05-09 Phase B1 audit's `claude-infra` dimension surfaced (see `agent_docs/audits/2026-05-09/claude-infra.md`): stale paths, broken cross-links, outdated test counts, framework-version drift, removed concepts, and skill / agent inventory mismatches.

This is the **read-and-report** complement to `audit-mode` (`.claude/skills/audit-mode/SKILL.md`). They share the same discipline (no auto-fix, cite path:line, prioritize) but `audit-mode` audits **the codebase**; `claude-infra-sync` audits **the agent-facing instructions**.

## When to run

- **End of every major Phase or Wave.** The 2026-05-09 audit produced ~12 drift items; one Phase later half of them will have moved or compounded.
- **After any rename / restructure** under `agent_docs/`, `docs/`, `backend/src/`, or `frontend/src/`. Renames always leave dangling references in agent files.
- **Before dispatching a fresh audit cycle.** A clean sync state means the auditors aren't re-finding the same drift the previous cycle already flagged.
- **On demand** when an agent run produced confused output suggesting it followed a stale instruction (e.g., wrote into `architecture_plans/` because the agent file still pointed there).

Cadence guidance: run **at least once per Phase**. CI integration is reasonable but optional — the skill is fast (~2 min) and false-positive-prone enough that a human-in-the-loop review on the report is the higher-leverage workflow.

## Inviolable rules

- **Never auto-fix.** This skill surfaces drift; humans (or a follow-up `docs-refactorer` / `architect` dispatch) resolve it. Auto-fix risks introducing the wrong correction silently.
- **No code changes.** The only file written is the report at `agent_docs/sync-checks/YYYY-MM-DD/REPORT.md`. No edits to `CLAUDE.md`, `.claude/`, source, or tests.
- **Cite path:line.** Every finding cites a file path and line number. A finding without a citation is not actionable.
- **Calibrate.** Use BLOCKER / WARN / NIT (see "Severity calibration" below). 5–20 findings total is the target band for a healthy project.
- **Treat PROGRESS.md as the source of truth** for phase, test counts, and live milestones. When agent files claim something different, PROGRESS.md wins.

## Pre-work — snapshot the current state

Before running the lint passes, build a snapshot. The findings will reference these:

```bash
# 1. Inventory of Claude infra files
find .claude/agents -name "*.md" | sort
find .claude/skills -name "SKILL.md" | sort

# 2. Total Claude infra volume
wc -l CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md | tail -1

# 3. Source-of-truth version / count signals
grep -E '"react"|"react-dom"|"@types/react"' frontend/package.json
grep -E '^requires-python|^python =' backend/pyproject.toml
grep -E 'Total Tests|backend|frontend' PROGRESS.md | head -5

# 4. Repo structure signals (for stale-path checks)
ls -la docs/ agent_docs/ backend/src/zebu/ frontend/src/

# 5. Most recent task number (drives the "next number is N" check)
ls agent_docs/tasks/ | grep -E '^[0-9]' | sort -n | tail -1
```

Capture the outputs in scratch — they feed the lint passes below.

## Lint passes

Each pass is independent. Run them in order; emit findings to a working list, then format the report at the end. The bundled helper at `.claude/skills/claude-infra-sync/check.sh` runs the simple grep-based subset of these passes; everything past that requires the agent's judgment.

### Pass 1 — Stale paths

Every backtick-quoted path mentioned in `CLAUDE.md`, `.claude/agents/*.md`, or `.claude/skills/*/SKILL.md` must point at a file or directory that exists.

```bash
# Extract candidate paths (file-ish) and dedupe
grep -hoE '`[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.(md|py|ts|tsx|toml|json|yaml|yml)`' \
  CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md \
  | tr -d '`' | sort -u

# For each, check existence:
for p in <paths from above>; do
  [ ! -e "$p" ] && echo "MISSING: $p"
done
```

Also check directory-shaped references:

```bash
grep -hoE '`[A-Za-z0-9_./-]+/`' CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md \
  | tr -d '`' | sort -u
```

Verify each directory exists. **Known false-positive class**: example paths inside fenced code blocks (e.g., a `agent_docs/tasks/NNN_short_name.md` placeholder with literal `NNN`). Filter those out — they're templates, not references.

The 2026-05-09 audit's `CLAUDE-P0-1` (`architecture_plans/` referenced but absent) is the canonical example of what this pass should catch.

### Pass 2 — Cross-references between Claude infra files

Each agent / skill referenced from another agent or skill or `CLAUDE.md` must exist.

```bash
# Skill references
grep -rhE '\.claude/skills/[a-z0-9-]+(/SKILL\.md)?' \
  CLAUDE.md .claude/ | grep -oE '\.claude/skills/[a-z0-9-]+' | sort -u

# Agent references
grep -rhE '\.claude/agents/[a-z0-9-]+\.md' \
  CLAUDE.md .claude/ | sort -u
```

For each, verify the target exists. Missing targets = **BLOCKER** (an agent reading the reference will follow it into nothing).

### Pass 3 — Skills inventory (CLAUDE.md ⇔ filesystem)

The "Project skills" table in `CLAUDE.md` must match `.claude/skills/`.

```bash
# What CLAUDE.md says exists (skill-table column 1)
awk '/^## Project skills/,/^## /' CLAUDE.md \
  | grep -oE '`[a-z0-9-]+`' | tr -d '`' | sort -u

# What actually exists
ls .claude/skills/ | sort -u
```

`diff` the two. Each side has a name:

- **In CLAUDE.md but missing on disk** = BLOCKER (broken promise to the agent).
- **On disk but missing from CLAUDE.md** = WARN (orphaned skill — the agent won't discover it).

### Pass 4 — Agents inventory (CLAUDE.md ⇔ filesystem)

Same shape as Pass 3 but for `.claude/agents/`.

```bash
awk '/^## Specialist agents/,/^## /' CLAUDE.md \
  | grep -oE '`[a-z0-9-]+`' | tr -d '`' | sort -u

ls .claude/agents/ | sed 's/\.md$//' | sort -u
```

Diff and classify the same way (BLOCKER if CLAUDE.md promises a missing agent; WARN if an agent file is orphaned).

### Pass 5 — Test-count freshness

Any sentence claiming "N tests" / "N backend tests" / "Total: N" in `CLAUDE.md`, `.claude/`, or `README.md` should agree with `PROGRESS.md` (or be re-grounded by an actual run).

```bash
grep -rEn '\b[0-9]{3,4}\s*tests?\b' \
  CLAUDE.md README.md PROGRESS.md .claude/ docs/ 2>/dev/null
```

`PROGRESS.md` is the source of truth. Findings:

- **Mismatch with PROGRESS.md** = WARN (someone updated one and not the other).
- **All claims agree but disagree with the live count** (`task quality:backend` / `quality:frontend`) = NIT (PROGRESS.md and code are out of sync; that's a `docs-tidy` job).

Don't run the full test suite from this skill — it takes too long. Trust PROGRESS.md and flag the inconsistency for follow-up.

### Pass 6 — Framework / language version drift

Compare claims in agent files / `CLAUDE.md` to actual lock / manifest files.

```bash
# Find version claims
grep -rEn 'React [0-9]+\+?|Python [0-9]\.?[0-9]*\+?|Node [0-9]+|TypeScript [0-9]+\.[0-9]+' \
  CLAUDE.md .claude/

# Sources of truth
grep -E '"react"|"@types/react"' frontend/package.json
grep -E '^requires-python|^python =' backend/pyproject.toml
```

The 2026-05-09 audit's `CLAUDE-P1-3` (`frontend-swe.md` claimed "React 18+" while `frontend/package.json` is `^19.2.0`) was a textbook case. **Mismatch** = WARN.

### Pass 7 — Endpoint references in agent definitions

Any `/api/v1/...` literal in an agent file should resolve to an actual route handler in `backend/src/zebu/adapters/inbound/api/`.

```bash
# Find endpoint mentions
grep -rEn '/api/v[0-9]+/[A-Za-z0-9_/-]+' .claude/agents/ CLAUDE.md

# Source of truth — router files declare route prefixes / paths:
grep -rEn '@router\.(get|post|put|patch|delete)' backend/src/zebu/adapters/inbound/api/
```

Cross-reference. **Endpoint mentioned in agent file but no matching route** = BLOCKER (agent will write code calling a dead endpoint). **Endpoint matches but the agent file's HTTP verb is wrong** = WARN.

### Pass 8 — Removed concepts

Words that name an entity, port, or module in agent prose must still exist in code. This pass is the most judgment-heavy.

```bash
# Sample technical nouns from agent files (look for backtick-wrapped CamelCase / snake_case)
grep -hoE '`[A-Z][A-Za-z0-9]+`' .claude/agents/*.md CLAUDE.md | tr -d '`' | sort -u

# For each, verify it appears in the codebase:
for n in <names>; do
  if ! grep -rq "class $n\|def $n\|interface $n\|type $n" backend/src/ frontend/src/; then
    echo "ORPHAN CONCEPT: $n"
  fi
done
```

False positives are common (generic names like `Money`, `Portfolio` are real; doc-only names like `PortfolioCardProps` may be examples). Triage. **Confirmed orphan concept** = WARN.

### Pass 9 — Inconsistent terminology

Look for the same idea named differently across files. Common sources of drift in this repo (per the audit):

- "specialist agents" vs "subagents" vs "sub-agent" vs "agents"
- "Phase 5" vs "Phases A–F" vs "Phase A/B/C..."
- `subagent_type` (literal API param) vs `agent type` vs `Task tool`

```bash
# Term-counter for the four agent-naming variants
for term in "specialist agent" "subagent" "sub-agent" "specialist-agent"; do
  echo "=== $term ==="
  grep -rEn "$term" CLAUDE.md .claude/ | head -5
done
```

A repo that uses **all four** is drifting. Pick one (the audit recommended "specialist agents") and flag the rest. **Mixed terminology with >2 variants in active use** = NIT (or WARN if it leads to confusion in dispatch).

### Pass 10 — Single-source-of-truth checks

Some facts appear in three places (the 2026-05-09 audit's `CLAUDE-P2-1`): "next task number is N" lives in `CLAUDE.md`, `agent_docs/README.md`, and `before-starting-work/SKILL.md`. Either they all agree (and just propagate manually), or one drifts.

```bash
grep -rEn 'next (number|task) is (\*\*)?[0-9]+' \
  CLAUDE.md agent_docs/README.md .claude/skills/
```

If they disagree = WARN. If they agree but the actual filesystem (`ls agent_docs/tasks/ | sort -n | tail -1`) shows a different latest = WARN.

## Severity calibration (BLOCKER / WARN / NIT)

Mirror the calibration discipline in `audit-mode` but tuned for an instructions-as-code surface:

### BLOCKER — fix before next agent dispatch

A finding is BLOCKER if **at least one** of:

- Reference to a path / file / module that doesn't exist (agent will break or silently no-op).
- Skill / agent in CLAUDE.md inventory missing on disk (agent reads CLAUDE.md, tries to invoke, fails).
- API endpoint literal that has no route handler (generated client code will 404).
- Two agent files actively contradict each other on a load-bearing rule (the orchestrator can't pick).

The 2026-05-09 audit had **3 P0s** in the claude-infra dimension; expect ~1–3 BLOCKERs in a healthy run.

### WARN — fix before end of phase

Real drift, not actively breaking, but compounds:

- Version claim mismatch (React 18+ vs `^19.2.0`).
- Test-count claim out of sync with PROGRESS.md.
- Orphaned skill on disk not in CLAUDE.md inventory.
- Endpoint HTTP verb mismatch.
- Single-source-of-truth fact drifting across files.

Expect ~3–8 WARNs in a healthy run.

### NIT — defer to next docs-tidy or P3 cleanup

Aesthetics, micro-inconsistencies, terminology drift that doesn't block dispatch. Listing it is enough; the report doesn't need a fix scope.

## Calibration cross-checks

Before writing the report, sanity-check:

- **Does each BLOCKER actually break agent dispatch?** If you'd be okay running an agent against the current state without fixing this, demote to WARN.
- **Are findings cited?** Every entry has `path:line` (or `path:line-range`). No citation = no finding.
- **Did you check both directions of inventory?** Pass 3 / Pass 4 are bidirectional — orphaned skills are easier to miss than missing skills. Didn't find any orphans? Re-run.
- **Are NIT findings adding signal?** A report with 14 NITs and 2 WARNs is noise. Either promote some NITs or trim them.

## Output — the report

Write to `agent_docs/sync-checks/YYYY-MM-DD/REPORT.md`. Use the **dispatch date** (today's date) — even if a sync runs across midnight, all of one cycle's output lives in one dated directory. Multiple runs in one day overwrite (or append a `-2` suffix).

### Report skeleton

```markdown
# Claude Infra Sync — <YYYY-MM-DD>

- **Run by**: <agent or human name>
- **Trigger**: <on-demand | end-of-Phase-N | end-of-Wave-N | scheduled>
- **Scope**: `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`
- **Snapshot**: `<N agents>`, `<N skills>`, `<N total lines of Claude infra>`

## Summary

| Severity | Count |
|---|---:|
| BLOCKER | <n> |
| WARN | <n> |
| NIT | <n> |
| **Total** | **<n>** |

**Top concern (one sentence)**: <single most important finding, plain English, naming the affected file>.

## BLOCKER

### [BLOCKER-1] <Short title>

- **Where**: `path/to/file.md:LINE` — `quoted excerpt`
- **Drift**: <what the file says> vs. <what's actually true>
- **Why it matters**: <how this misleads an agent dispatch>
- **Suggested fix**: <one-liner the docs-refactorer / architect can act on>

## WARN

### [WARN-1] ...

## NIT

### [NIT-1] ...

## Inventory snapshot

| Surface | Count | Notes |
|---|---:|---|
| Agents (`.claude/agents/`) | <n> | <list> |
| Skills (`.claude/skills/`) | <n> | <list> |
| CLAUDE.md lines | <n> | |
| Total Claude infra lines | <n> | |

## Recommended follow-up

- BLOCKERs → `docs-refactorer` PR titled `fix(claude-infra): resolve drift from <YYYY-MM-DD> sync`
- WARNs → bundle into the next phase's docs-tidy pass
- NITs → defer
```

Real example to model on: the audit-style report at `agent_docs/audits/2026-05-09/claude-infra.md` (the prose differs because it was an audit, not a sync — but the layout, citations, and severity discipline are the same).

## Reporting back to the orchestrator (or user)

After the report lands, reply with under ~150 words:

- **File path** of the report.
- **Severity counts**: `BLOCKER: N / WARN: N / NIT: N`.
- **Top concern** in one sentence.
- **Anything urgent** (a BLOCKER that should be fixed before the next agent dispatch).
- **What this didn't cover** (passes you skipped because the data wasn't accessible — e.g., couldn't reach the running test suite).

Example:

> Wrote `agent_docs/sync-checks/<YYYY-MM-DD>/REPORT.md`. BLOCKER: 1 / WARN: 4 / NIT: 3. Top concern: `frontend-swe.md:62` still references `JSX.Element` (codebase uses `React.JSX.Element` everywhere). One BLOCKER: `architect.md:28-38` points to `architecture_plans/` which doesn't exist. Recommend `docs-refactorer` dispatch this week. Skipped Pass 7 (endpoint references) — none found in agent files this run.

## Anti-patterns

- **Don't auto-fix.** The skill surfaces drift. Humans or a follow-up dispatch resolve it. Auto-fix risks introducing the wrong correction silently — there's no good signal for "is this stale or merely speculative?"
- **Don't grep for everything.** Each pass has a target signal class; don't expand a pass into a generic content audit. Inconsistent terminology (Pass 9) ≠ inconsistent prose style.
- **Don't run on every PR.** This skill is per-Phase or per-Wave granularity. Per-PR runs will dominate the noise budget without finding new drift.
- **Don't promote NITs to look thorough.** If you have 1 BLOCKER and 0 WARNs, the report says "1 BLOCKER and 0 WARNs". Padding the WARN section with stretches dilutes the signal.
- **Don't audit code in this skill.** This skill audits **agent-facing instructions**. The codebase audit is `audit-mode`. Keep them separate; don't conflate.
- **Don't skip the snapshot.** The pre-work snapshot is what makes the report trustworthy six months later — without it, "PROGRESS.md said 1,142 tests" is unverifiable.

## See also

- `.claude/skills/audit-mode/SKILL.md` — the read-and-report discipline this skill mirrors, applied to the codebase rather than the agent instructions.
- `.claude/skills/docs-tidy/SKILL.md` — periodic BACKLOG / PROGRESS / README cleanup; the natural place to land WARN-level fixes from a sync run.
- `.claude/skills/before-starting-work/SKILL.md` — the implementation-mode pre-work checklist (this skill is its drift-detection counterpart).
- `.claude/skills/claude-infra-sync/check.sh` — bundled helper for the simple grep-based subset of these passes (Pass 1, 3, 4, 5, 6 prerequisites).
- `agent_docs/audits/2026-05-09/claude-infra.md` — the audit report whose `CLAUDE-P1-2` finding produced this skill.
- `docs/planning/agent-platform-proposal.md` §B7 — the proposal section that scoped this skill.
