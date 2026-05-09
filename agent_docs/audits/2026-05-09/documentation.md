# Documentation Audit — Phase B1

**Auditor**: `docs-refactorer`
**Slug**: `docs`
**Date**: 2026-05-09
**Dimension**: Documentation
**Scope**: `docs/`, `README.md`, `CONTRIBUTING.md`, `BACKLOG.md`, `PROGRESS.md`, `agent_docs/README.md`, `agent_docs/mcp-tools.md`, `mkdocs.yml`

---

## Summary

The published docs site (`docs/`) is in noticeably worse shape than the agent infra (which Phase A just sharpened) or the production code itself. Most files were last touched in **January 2026** and never reconciled to the **March 8 2026** Phase 4 milestone, let alone the **May 9 2026** Phase A migration. Key facts the docs assert (test counts, infra path, project plan link, current Phase, even whether `resume-from-here.md` exists) are flat-out wrong. A fresh dev or fresh agent following `README.md` would hit a dead link before ever cloning successfully.

The published `docs/README.md` (mkdocs Home) actively links into `docs/archive/` from main nav — so users coming in via the docs site land on archive material as if it were live.

I also found a substantial pile of stale chronological artifacts in `docs/archive/`, `docs/architecture/archived/`, and `docs/planning/archive/`. Most of these have **no ongoing reference value** — they're old "we reorganized this" cleanup summaries, superseded reorg proposals, and a reorg complete log. Per the docs-refactorer policy ("the migration is done; the meta is noise") they should be deleted, not kept.

| Priority | Count |
|---|---|
| P0 | 4 |
| P1 | 6 |
| P2 | 5 |
| P3 | 2 |
| **Total** | **17** |

**Top concern**: `README.md` is the front door for any new dev or agent — and it currently sends them to **a Copilot setup script that no longer exists** (`./.github/copilot-setup.sh`), tells them to run **`uv run uvicorn papertrade.main:app`** (wrong module — it's `zebu.main:app`), points to **`docs/planning/project_plan.md`** (which lives in `docs/planning/archive/`), and references **`docs/TESTING_STRATEGY.md`** (doesn't exist). This is the single highest-leverage thing to fix.

---

## P0 — Actively Misleading

### P0-1. README setup instructions are broken end-to-end

**File**: `/Users/timchild/github/PaperTrade/README.md`

Multiple breaks in the same setup flow:

- **L154** — `./.github/copilot-setup.sh` no longer exists; this was deleted in the Phase A Copilot-infra removal. Onboarding flow dies on first command.
- **L193** — `uv run uvicorn papertrade.main:app --reload` — module renamed to `zebu` in PR #132 (Jan 14). Correct command is `uv run uvicorn zebu.main:app --reload`.
- **L29** — `[Project Plan](docs/planning/project_plan.md)` — file moved to `docs/planning/archive/project_plan.md` in PR #129/#131. Link 404s.
- **L460** — `See [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for details.` — file does not exist (testing docs live under `docs/testing/`).
- **L573** — `See [project_plan.md](docs/planning/project_plan.md)` — same dead link, second instance.
- **L585** — `See [project strategy](docs/planning/project_strategy.md)` — file exists but path from root works; check OK.
- **L406** — Project Structure tree includes `agent_progress_docs/` which no longer exists (it's `agent_docs/`).
- **L389-L405** — Project structure tree omits `CLAUDE.md`, `.claude/` directories, and `agent_docs/` subdirectories that the CLAUDE.md "Where things live" table now treats as canonical.

**Impact**: A fresh dev/agent following the README cannot complete setup. P0 because this is the canonical onboarding doc.

**Fix**: Rewrite Quick Start to point at `task setup` (canonical), `task dev:backend` / `task dev:frontend`. Remove all references to `copilot-setup.sh`, `papertrade.main`, `project_plan.md`, `TESTING_STRATEGY.md`. Sync Project Structure tree to current reality (the `CLAUDE.md` table is the source of truth).

---

### P0-2. `resume-from-here.md` still present and linked from main docs nav

**Files**:
- `/Users/timchild/github/PaperTrade/docs/archive/resume-from-here.md` (still on disk)
- `/Users/timchild/github/PaperTrade/docs/README.md` (L84 — actively links to it from main nav)
- `/Users/timchild/github/PaperTrade/docs/archive/README.md` (L17 — describes it as "Session Handoffs")

The Phase A status block in `agent-platform-proposal.md` (L17) explicitly claims `resume-from-here.md` was deleted as part of the cleanup. **It wasn't — it was moved to `docs/archive/` and is still being linked**. The doc itself (Jan 11, 2026, Proxmox prototype handoff) has zero ongoing reference value.

**Fix**: Delete `docs/archive/resume-from-here.md` outright. Remove the row from `docs/README.md` archive table. Remove the bullet from `docs/archive/README.md`. Per `docs-tidy` policy ("don't archive items just because they're old; the git history is the archive"), this is a delete, not an archive move.

---

### P0-3. Test count claims are wildly inconsistent across the docs site

**Confirmed source of truth** (from PROGRESS.md L22, L393, and the proposal): **831 backend + 311 frontend = 1,142 tests** (March 8 2026).

**Stale claims still live**:

| File | Line | Wrong claim |
|---|---|---|
| `CONTRIBUTING.md` | L237 | `task test           # All tests (483 total)` |
| `CONTRIBUTING.md` | L240 | `task test:backend   # Backend (402 tests)` |
| `CONTRIBUTING.md` | L241 | `task test:frontend  # Frontend (81 tests)` |
| `docs/planning/executive-summary.md` | L15 | `796 automated tests (571 backend + 225 frontend)` |
| `docs/planning/executive-summary.md` | L115 | `Testing: 81%+ coverage, 796 tests passing` |
| `docs/planning/executive-summary.md` | L125 | `Backend: 571 tests passing` |
| `docs/planning/executive-summary.md` | L126 | `Frontend: 225 tests passing` |
| `docs/planning/features.md` | L100 | `571 backend + 225 frontend tests` |
| `docs/planning/features.md` | L176 | `Current test suite: 796 tests` |
| `docs/testing/README.md` | L48 | `Total: 796+ tests (571 backend + 225 frontend)` |
| `docs/testing/standards.md` | L256 | `All tests passing (796+ tests)` |

**Impact**: Multiple values across multiple authoritative-looking docs — readers/agents will trust the wrong number. Resolved Q in the proposal calls for "pick a source of truth"; that source is now PROGRESS.md.

**Fix**: Globally replace `796`/`571 backend`/`225 frontend`/`483`/`402 backend`/`81 frontend` with `1,142`/`831 backend`/`311 frontend`. Add a one-liner at the top of `docs/testing/README.md` saying "Test counts are reconciled in PROGRESS.md; this doc shows shape only."

---

### P0-4. `docs/planning/executive-summary.md` describes a different Phase 4 than what shipped

**File**: `/Users/timchild/github/PaperTrade/docs/planning/executive-summary.md` (L72, L86–96)

The exec summary still says:
- `⚠️ No limit/stop orders - Market orders only (planned Phase 4)` (L72)
- `Phase 4: Professional Features (2026)` — Advanced order types, WebSockets, multi-provider data
- `Phase 5: Automation (2027+)` — Algorithmic trading

But what actually shipped under "Phase 4" is **Trading Strategies & Backtesting** (PRs #207, #208 — see `PROGRESS.md` L19, `roadmap.md` L88, the proposal). Phase 5 in the current plan is the **Agent Platform Proposal**, *not* "Automation 2027+."

This is a genuine accuracy bug — anyone reading this exec summary will think Phase 4 hasn't started and a totally different Phase 5 is two years away. The doc still calls itself `v1.2.0` in the header (L3), but the project shipped **v1.0.0** on the CD pipeline (March 8); v1.2.0 was an interim chart-engine release.

**Same disease**: `docs/planning/features.md` L176 ("796 tests"); `docs/planning/phase4-technical-plan.md` (the entire file, L1–L40) describes Phase 4 as "Advanced Order Types, WebSockets, Transaction Fees" — that's the *old* Phase 4 plan that never shipped. It is now stale meta-content.

**Fix**:
- Rewrite `executive-summary.md` to match reality (Phase 4 = Strategies+Backtesting ✅; Phase 5 = Agent Platform per proposal, in progress).
- **Delete `docs/planning/phase4-technical-plan.md`** outright — the actual Phase 4 architecture is documented at `docs/architecture/phase4-trading-strategies.md` (1052 lines, accurate, dated March 8). Keeping the obsolete plan is exactly the "stale superseded how-to" delete-target the docs-refactorer policy describes.

---

## P1 — Dead Links / Diverging Duplicates

### P1-1. CONTRIBUTING.md is structurally out of date

**File**: `/Users/timchild/github/PaperTrade/CONTRIBUTING.md`

- **L23** — `./.github/copilot-setup.sh` (removed; same break as P0-1).
- **L110** — `from papertrade.domain.value_objects.money import Money` — wrong module name.
- **L173** — `from papertrade.infrastructure.database import engine` — wrong module name.
- **L167, L321** — `[project_strategy.md](project_strategy.md)` — relative link from repo root resolves to nonexistent `./project_strategy.md`. Should be `docs/planning/project_strategy.md`.
- **L237–L241** — wrong test counts (covered in P0-3).
- **L283–L292** — Database section references `task db:reset`, `task db:shell`, `task db:seed`, `task db:migrate:create` — verify these tasks still exist in `Taskfile.yml` (some may have been renamed/removed). If absent, remove the section.
- L323 — points to `.claude/skills/orchestrate-zebu/SKILL.md` — good, that's correct now.

**Fix**: Patch all four module-path bugs and re-link `project_strategy.md` correctly. Verify the Taskfile claims.

---

### P1-2. `docs/README.md` (mkdocs Home) actively links archive content from main nav

**File**: `/Users/timchild/github/PaperTrade/docs/README.md` (L74–L88)

The published Home page has a full "Archive" section linking to nine archived files including `resume-from-here.md`, `proposed-reorganization.md`, `REORGANIZATION_COMPLETE.md` etc. Per the audit brief: archive content should NOT be linked from main pages. Burying it in the Home page surfaces it in search and gives it equal weight to live docs.

**Fix**: Strip the entire Archive section from `docs/README.md`. If archive content needs an index, put it in `docs/archive/README.md` (which already exists) and don't link to that index from the main Home page either.

---

### P1-3. `docs/planning/roadmap.md` has internal phase contradictions

**File**: `/Users/timchild/github/PaperTrade/docs/planning/roadmap.md`

- **L4 and L372** — disagree with each other on the file's own "Last Updated" (May 9, 2026 at top; January 26, 2026 at bottom).
- **L246-L249** — Target Milestones table still has `Phase 4a — Q2 2026 — In Progress (UX & monitoring)`, `Phase 4b — Advanced orders`, `Phase 4c — Multi-provider data`, `v2.0 Launch — Q4 2026`. **All of this is the *old* Phase 4 plan**; actual Phase 4 (Strategies+Backtesting) is already ✅ COMPLETE per L88. So the file simultaneously says Phase 4 is done (L88) AND in progress (L246) AND not started (L247–L249).
- **L101** — Quality line `1,142 tests` (✅ correct).
- **L131** — Phase 6 timeline says `Q2-Q4 2026 (in progress - monitoring and UX improvements already deployed)` — this is the old Phase 4 again, not Phase 6.
- **L209-L211, L327-L329** — fictional / coming-soon community channels (Discord, Email, Twitter @ZebuSim, feedback@zebu.com, monthly newsletter) — none of these exist; per Q5 and Q6 in the proposal this is a personal project that should not pretend to have community infra.

**Fix**: Single edit — bring the entire Milestones table and Phase 6 framing into line with the new phase narrative (4 done, 5 in progress per agent-platform-proposal). Strip the fictional community channels. Reconcile the two "Last Updated" dates.

---

### P1-4. `docs/architecture/technical-boundaries.md` predates Phase 4

**File**: `/Users/timchild/github/PaperTrade/docs/architecture/technical-boundaries.md`

- L4 — `Version: Phase 3 Complete` (we're past Phase 4).
- L153–L156 — limitation mitigations all framed as "Phase 4" — but Phase 4 already shipped a different scope. These should be re-pointed to Phase 6 / future per the new roadmap.

**Fix**: Update version header and re-frame mitigations to use the new phase numbers. Lightweight.

---

### P1-5. `docs/planning/future-ideas.md` instructs people to write to a deleted file

**File**: `/Users/timchild/github/PaperTrade/docs/planning/future-ideas.md` (L46)

> *Add new ideas by editing this file. Move items to `project_plan.md` when they become concrete plans.*

`project_plan.md` no longer exists at that path. Also, L46 mentions Kubernetes/multi-region/CDN as "Infrastructure Ideas" — these are misleading because production deploys to Proxmox VM (not AWS), so these aren't latent ideas but actively contradictory.

**Fix**: Replace `project_plan.md` with `roadmap.md`. Drop the AWS-flavored infrastructure ideas.

---

### P1-6. AWS CDK is referenced as live infra across many docs but `infrastructure/` directory does not exist

**Files affected**:

- `README.md` L101 (Tech Stack table — `IaC | AWS CDK (Python)`)
- `README.md` L405 (`├── infrastructure/          # AWS CDK`)
- `docs/planning/project_strategy.md` L45, L158
- `docs/architecture/principles.md` L31 (`(Docker, AWS CDK, DB Config)`)
- `docs/architecture/README.md` (architecture diagrams imply CDK in Infrastructure layer)
- `CLAUDE.md` L11 (`AWS CDK (Python)`)

Verified: `/Users/timchild/github/PaperTrade/infrastructure/` does NOT exist. Production deploy is via `scripts/proxmox-vm/` to a Proxmox VM (per `docs/deployment/proxmox-vm-deployment.md` and `docs/planning/deployment_strategy.md` Stage 1). `docs/planning/deployment_strategy.md` mentions Stage 2 = AWS as future, but the docs as-shipped frame AWS CDK as *current* infra.

**Impact**: Architectural docs lie about what infrastructure actually exists. An onboarding agent trying to follow Clean Architecture diagrams will look for an `infrastructure/` AWS CDK module that isn't there.

**Fix**: Strip "AWS CDK" from current-state docs (`README.md` Tech Stack, `principles.md`, `project_strategy.md`, `CLAUDE.md`). Replace with "Docker Compose + Proxmox VM (`scripts/proxmox-vm/`)". Keep AWS as Stage 2 (future) only in `deployment_strategy.md`.

---

## P2 — Cleanup / Archive Moves / Deletes

### P2-1. `docs/architecture/phase4-trading-strategies.md` is fine but heavily duplicated

The 1,052-line architecture doc is the source of truth for Phase 4. But chunks of its content also live in `phase4-technical-plan.md` (now stale, see P0-4) and architectural-overview content is duplicated in `docs/architecture/README.md`, `docs/planning/project_strategy.md`, `docs/planning/executive-summary.md`, `README.md` Architecture section, and `CLAUDE.md`. **Six near-identical "Domain → Application → Adapters → Infrastructure" diagrams across the codebase.**

**Fix (small)**: Pick one as canonical (`docs/architecture/principles.md` is the cleanest and was just promoted in Phase A). All other diagrams should be a one-line "see principles.md" instead of duplicating. Reduces drift surface area.

---

### P2-2. `docs/planning/phase4-technical-plan.md` should be deleted (recommend OUTRIGHT DELETE)

**File**: `/Users/timchild/github/PaperTrade/docs/planning/phase4-technical-plan.md` (442 lines)

It describes a Phase 4 ("Advanced Order Types, WebSockets, Transaction Fees, Multi-provider Market Data") that was **abandoned** when the actual Phase 4 became Trading Strategies + Backtesting. It is meta-documentation about a never-shipped plan. The mkdocs nav doesn't even reference it. Per docs-refactorer policy: "Outdated technical docs … delete. Redundant / superseded how-to guides … delete."

**Recommend OUTRIGHT DELETE.**

---

### P2-3. `docs/archive/` contains pure cleanup-meta with no archival value

**Files in `/Users/timchild/github/PaperTrade/docs/archive/`** that fit the docs-refactorer "meta-documentation about completed migrations / refactors → delete (the migration is done; the meta is noise)" rule:

- `CLEANUP_SUMMARY.md` — recap of January 2026 cleanup work. **Recommend DELETE.**
- `CONSOLIDATION_SUMMARY.md` — recap of Docker/CI/CD consolidation. **Recommend DELETE.**
- `REORGANIZATION_COMPLETE.md` — recap of an old reorganization. **Recommend DELETE.**
- `proposed-reorganization.md` — the *proposal* for a reorganization that was completed two reorganizations ago. **Recommend DELETE.**
- `PROTOTYPE_GUIDE.md` — prototype access guide; the prototype is gone. **Recommend DELETE.**
- `resume-from-here.md` — covered in P0-2. **Recommend DELETE.**
- `e2e-testing-alpha-vantage-investigation.md` — investigation completed; outcome was integrated long ago. **Recommend DELETE** (or archive only if there's a specific Alpha Vantage decision worth preserving — quick read suggests not).
- `foundation-evaluation-2026-01-03.md` — evaluation snapshot from Jan 2026; lots of stale content (483 tests, etc.). Borderline — it has *some* historical-decision-record value. **Recommend ARCHIVE keep** (genuine snapshot artifact).
- `progress-archive.md`, `progress-archive-2025-12-to-2026-01.md` — chronological progress reports. **Keep** (genuine archival).
- `seed-files/` — original project seed. **Keep** (chronological, ~5 small files).

**Net**: 7 of 11 archive files should be deleted, 4 kept. `docs/archive/README.md` rewritten to reflect what's actually in there.

---

### P2-4. `docs/architecture/archived/` — same disease, less critical

Architecture-archived has Phase 1 and Phase 2 ADRs (e.g., `adr-001-caching-strategy.md`, `adr-002-rate-limiting.md`, `adr-003-background-refresh.md`, `adr-004-configuration.md`) and a `phase3-refined/` subfolder. These ADRs describe the original `papertrade` namespace and have ~16 stale `papertrade:price`, `from papertrade.infrastructure...` references inside them. Per the policy, ADRs are archive-keep, but they should be tagged so search engines / agents see "this is historical."

**Fix**: Add a `**Status**: Archived (original PaperTrade-era ADR)` callout at the top of each `adr-*.md` so an agent reading them through search doesn't think they're describing current state. **Don't delete** — these are decision records.

---

### P2-5. `docs/deployment/migration-checklist.md` not in mkdocs nav

**File**: `/Users/timchild/github/PaperTrade/docs/deployment/migration-checklist.md`

Lives in `docs/` but isn't in `mkdocs.yml` nav. Either add it to the Deployment section or move it under `agent_docs/` if it's an internal procedure. Currently invisible to docs-site readers.

**Fix**: Add `Migration Checklist: deployment/migration-checklist.md` to mkdocs nav under Deployment.

---

## P3 — Cosmetic

### P3-1. Inconsistent "Last Updated" dates everywhere

Every doc has a different last-updated date (Jan 4, Jan 9, Jan 11, Jan 26, March 7, March 8, May 9), and `roadmap.md` has *two contradictory* dates in the same file (L4 vs L372). Establishing one convention (e.g., "Last Updated only at top, refreshed on substantive change, dated YYYY-MM-DD") would help.

### P3-2. `agent_docs/mcp-tools.md` references the wrong workspace path

**File**: `/Users/timchild/github/PaperTrade/agent_docs/mcp-tools.md` L28, L31, L37

Hard-codes `/Users/timchild/github/Zebu` as workspace root. Repo path is `/Users/timchild/github/PaperTrade`. Also references `pylanceUpdatePythonEnvironment` etc. — this is a Pylance-MCP set up via VSCode, but mostly relevant only to agents using VSCode + Pylance. Shouldn't block but worth fixing if anyone ever copies a snippet.

---

## Recommended OUTRIGHT DELETIONS (vs archive moves)

Per the docs-refactorer "be aggressive about deletion" stance:

| File | Reason |
|---|---|
| `docs/archive/resume-from-here.md` | Session handoff for finished work; Phase A claimed this was deleted already (P0-2) |
| `docs/planning/phase4-technical-plan.md` | Plan for an abandoned Phase 4 scope; superseded by `docs/architecture/phase4-trading-strategies.md` (P0-4 / P2-2) |
| `docs/archive/CLEANUP_SUMMARY.md` | Cleanup-meta; migration is done |
| `docs/archive/CONSOLIDATION_SUMMARY.md` | Cleanup-meta; migration is done |
| `docs/archive/REORGANIZATION_COMPLETE.md` | Cleanup-meta; migration is done |
| `docs/archive/proposed-reorganization.md` | Proposal for a reorg that's been replaced twice |
| `docs/archive/PROTOTYPE_GUIDE.md` | Prototype is gone |
| `docs/archive/e2e-testing-alpha-vantage-investigation.md` | Investigation closed; outcome integrated |

That's **8 files** for outright deletion. None has ongoing reference value; git history preserves them if anyone ever needs them.

**Keep in archive (true chronological / decision-record artifacts)**: `docs/archive/progress-archive.md`, `docs/archive/progress-archive-2025-12-to-2026-01.md`, `docs/archive/foundation-evaluation-2026-01-03.md`, `docs/archive/seed-files/`, the `docs/architecture/archived/adr-*.md` set, `docs/planning/archive/strategic-plan-2026-01-14.md`, `docs/planning/archive/project_plan.md`.

---

## Non-findings (verified clean)

- `agent_docs/README.md` — accurate, post-Phase-A, no stale refs
- `docs/architecture/principles.md` — clean, just promoted in Phase A (only nit: AWS CDK in diagram, see P1-6)
- `docs/architecture/phase4-trading-strategies.md` — accurate, dated March 8 2026
- `docs/USER_GUIDE.md` — clean, March 7 2026 dated, matches deployed app
- `docs/deployment/proxmox-vm-deployment.md` — actually a *strong* runbook; end-to-end actionable, prerequisites explicit, recovery paths covered. Best file in the set.
- `docs/deployment/README.md` — clean index
- `docs/monitoring/runbook.md` (first 40 lines reviewed) — looks operationally usable
- `mkdocs.yml` — nav is mostly correct (one missed file, P2-5)

No remaining live references to the deleted Phase A targets (`.github/copilot-instructions.md`, `.github/agents/`, `agent_docs/reusable/`, `agent_docs/orchestration-guide.md`) — confirmed. All hits land in `docs/archive/`, `docs/architecture/archived/`, `docs/planning/archive/`, or `agent_docs/tasks/archive/`. Phase A's removal pass was clean on this dimension.

---

## File pointers (absolute)

- `/Users/timchild/github/PaperTrade/README.md`
- `/Users/timchild/github/PaperTrade/CONTRIBUTING.md`
- `/Users/timchild/github/PaperTrade/PROGRESS.md`
- `/Users/timchild/github/PaperTrade/BACKLOG.md`
- `/Users/timchild/github/PaperTrade/CLAUDE.md`
- `/Users/timchild/github/PaperTrade/docs/README.md`
- `/Users/timchild/github/PaperTrade/docs/USER_GUIDE.md`
- `/Users/timchild/github/PaperTrade/docs/architecture/README.md`
- `/Users/timchild/github/PaperTrade/docs/architecture/principles.md`
- `/Users/timchild/github/PaperTrade/docs/architecture/technical-boundaries.md`
- `/Users/timchild/github/PaperTrade/docs/architecture/authentication.md`
- `/Users/timchild/github/PaperTrade/docs/architecture/phase4-trading-strategies.md`
- `/Users/timchild/github/PaperTrade/docs/planning/roadmap.md`
- `/Users/timchild/github/PaperTrade/docs/planning/executive-summary.md`
- `/Users/timchild/github/PaperTrade/docs/planning/features.md`
- `/Users/timchild/github/PaperTrade/docs/planning/future-ideas.md`
- `/Users/timchild/github/PaperTrade/docs/planning/phase4-technical-plan.md` (DELETE candidate)
- `/Users/timchild/github/PaperTrade/docs/planning/project_strategy.md`
- `/Users/timchild/github/PaperTrade/docs/planning/deployment_strategy.md`
- `/Users/timchild/github/PaperTrade/docs/planning/agent-platform-proposal.md`
- `/Users/timchild/github/PaperTrade/docs/deployment/proxmox-vm-deployment.md`
- `/Users/timchild/github/PaperTrade/docs/deployment/migration-checklist.md`
- `/Users/timchild/github/PaperTrade/docs/deployment/README.md`
- `/Users/timchild/github/PaperTrade/docs/testing/README.md`
- `/Users/timchild/github/PaperTrade/docs/testing/standards.md`
- `/Users/timchild/github/PaperTrade/docs/testing/e2e-guide.md`
- `/Users/timchild/github/PaperTrade/docs/archive/` (entire directory — see deletion list)
- `/Users/timchild/github/PaperTrade/agent_docs/README.md`
- `/Users/timchild/github/PaperTrade/agent_docs/mcp-tools.md`
- `/Users/timchild/github/PaperTrade/mkdocs.yml`
