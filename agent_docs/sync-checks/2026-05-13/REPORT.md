# Claude Infra Sync — 2026-05-13

- **Run by**: orchestrator subagent (end-of-Phase-J closeout)
- **Trigger**: end-of-Phase-J — seven PRs landed 2026-05-11/12 (#272–#277, #279) covering Task #212 (multi-layer data warmth) + Task #213 (Pattern B QUEUE-mode triggers)
- **Scope**: `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`
- **Snapshot**: 7 agents, 8 skills, **2,241** total lines of Claude infra (up from 2,193 in 2026-05-09 sync — `orchestrate-zebu` grew by ~48 lines for the Wave-closeout section)

## Summary

| Severity | Count |
|---|---:|
| BLOCKER | 3 |
| WARN | 5 |
| NIT | 4 |
| **Total** | **12** |

**Top concern (one sentence)**: `CLAUDE.md:3` still claims "Phase 4 complete … Phase A done, Phase B in progress" — every dispatched agent reads this first and gets a 4-month-stale picture (Phases A through J have all shipped end-to-end; the trigger system + data-warmth subsystem are deployed to prod).

The 2026-05-09 sync's two BLOCKERs are both fixed: `backend/pyproject.toml` is now `requires-python = ">=3.13"`, and `backend/docs/SCHEDULER.md` no longer references `architecture_plans/`. Three new BLOCKERs surfaced this cycle — all in `CLAUDE.md` itself, all stemming from the document not having been touched since the original 2026-05-09 dispatch. Drift is concentrated in **status / phase claims** and **single-source-of-truth task numbering**, exactly the failure mode this skill exists to catch.

---

## BLOCKER

### [BLOCKER-1] `CLAUDE.md` phase status is ~4 months stale — claims "Phase A done, Phase B in progress" while Phases A–J are all shipped

- **Where**:
  - `CLAUDE.md:3` — `**Phase 4 complete, v1.0.0 deployed** … (agent-driven trading, Phases A–F; Phase A done, Phase B in progress).`
  - `CLAUDE.md:98` — `The active proposal is \`docs/planning/agent-platform-proposal.md\` — six phases (A–F) to evolve Zebu into an agent-driven trading platform`
  - `CLAUDE.md:100` — `Status: Phase A (this Claude infra migration) is in progress as of 2026-05-09. Phase B is Task #210 + API-key auth + \`ExplorationTask\` queue.`
- **Drift**: Reality per `docs/planning/agent-platform-completed.md` + `docs/planning/agent-platform-next-steps.md`:
  - Phase A (Claude infra modernization): done 2026-05-09 (PR #210)
  - Phase B (codebase audit + 5 waves): done 2026-05-09 (22 PRs, #211–#234)
  - Phase C (live execution + API-key auth + ExplorationTask): done 2026-05-09 (5 PRs)
  - Phase D Wave 1+2 (MCP server read + write): done 2026-05-10 (#241, #242)
  - Phases H/I/E/F/G (agent-loop UX, fonts, parameter sweep, scheduled triggers, observability): done 2026-05-10 (PRs #249–#268)
  - Phase J (data warmth subsystem + Pattern B queue triggers): done 2026-05-11/12 (PRs #272–#279)
  - The original proposal at `docs/planning/agent-platform-proposal.md` has been **superseded** by `agent-platform-completed.md` (historical) and `agent-platform-next-steps.md` (forward).
- **Why it matters**: This is the first thing every dispatched agent reads. An agent following CLAUDE.md verbatim will assume API-key auth doesn't exist (it does, since PR #237 / Phase C2), assume MCP isn't built (it is, with 23 tools), and assume triggers aren't shipped (they are — full pipeline including Pattern B queue mode in #276). This actively misroutes work scoping: "design API-key auth" tasks would re-implement what already exists.
- **Suggested fix**: Rewrite the intro lines:
  - Line 3: `**Phase J complete**, v1.0.0 deployed to \`https://zebutrader.com\`. The agent-platform plan has shipped end-to-end through Phase J — see \`docs/planning/agent-platform-completed.md\` (historical) and \`docs/planning/agent-platform-next-steps.md\` (active forward plan: multi-provider invocation + agent-driven backtests).`
  - Line 98: replace "six phases (A–F)" with a pointer to the next-steps doc.
  - Line 100: delete the "Status" line entirely — phase status belongs in `PROGRESS.md` and the planning docs, not CLAUDE.md.

### [BLOCKER-2] `CLAUDE.md:7` says "Clerk auth (Bearer JWT only — no API key path yet)" — contradicts `CLAUDE.md:105` which documents the API-key path in detail

- **Where**:
  - `CLAUDE.md:7` — `Clerk auth (Bearer JWT only — no API key path yet).`
  - `CLAUDE.md:105` — `**Auth**: two paths coexist — Clerk Bearer JWT for humans, and API key (Phase C2) for machine identities (agents, scheduled tasks, MCP servers). Agents authenticate by minting a key at \`POST /api/v1/api-keys\` (Clerk-gated)…`
- **Drift**: Line 7 is wrong; line 105 is right. The API-key path shipped in PR #237 (Phase C2) and is mounted at `backend/src/zebu/main.py:178` as `api_keys_router` with prefix `/api/v1`. The router source is `backend/src/zebu/adapters/inbound/api/api_keys.py` (`prefix="/api-keys"`, `POST /api-keys` + `GET ""` + `DELETE /{api_key_id}`).
- **Why it matters**: An agent reading line 7 will design code that ignores API-key auth (e.g., adding a new endpoint will only wire `CurrentUserDep` for Clerk JWTs, missing the `ApiKey` path). The two lines actively contradict each other; the orchestrator can't pick which the spec intends.
- **Suggested fix**: Replace `Clerk auth (Bearer JWT only — no API key path yet)` with `Clerk auth (Bearer JWT) + API key (Phase C2) — see line 105 for the dual-auth pattern.` Or just drop the parenthetical entirely; the detailed description at line 105 is the authoritative version.

### [BLOCKER-3] "Next task number is **211**" — actual latest is `213_queue_mode_triggers.md`; the next is **214**

- **Where** (all three sources of truth disagree with the filesystem):
  - `CLAUDE.md:92` — `For multi-step work, write a numbered task spec under \`agent_docs/tasks/NNN_short_name.md\` (the next number is **211** — most recent is \`210_live_strategy_execution.md\`, scoped but not started).`
  - `agent_docs/README.md:28` — `Write a spec at \`agent_docs/tasks/NNN_short_name.md\` (next number is **211** — most recent is \`210_live_strategy_execution.md\`)`
  - `.claude/skills/before-starting-work/SKILL.md:54` — `\`agent_docs/tasks/\` — open numbered task specs (the next is **211**)`
- **Drift**: `ls agent_docs/tasks/` shows the actual latest is `213_queue_mode_triggers.md` (Task #211 = `recent_activity_feed`, #212 = `data_warmth_subsystem`, #213 = `queue_mode_triggers` all landed during Phases H/I/E/F/G/J). Next available number is **214**. Also, "210 scoped but not started" is wrong — Task #210 (live strategy execution) was shipped in Phase C.
- **Why it matters**: An agent scoping a new task spec will pick `211_*` as the filename, silently overwriting `211_recent_activity_feed.md` (or, more likely, get confused when `ls` shows the file already exists and stop). All three citations are load-bearing — every spec authoring path goes through one of these.
- **Suggested fix**: Update all three citations to "next is **214** — most recent is `213_queue_mode_triggers.md` (Phase J)." Going forward, consider single-sourcing this to `agent_docs/README.md` and having the other two refer to it (the `claude-infra-sync` skill's Pass 10 was designed precisely for this drift case).

---

## WARN

### [WARN-1] `CLAUDE.md:106` says "Task #210's live executor **will** mirror" — future tense for already-shipped work

- **Where**: `CLAUDE.md:106` — `**Hot paths**: \`backend/src/zebu/application/services/backtest_executor.py\` is the canonical "iterate over days, generate signals, execute trades" loop — Task #210's live executor will mirror its structure.`
- **Drift**: Task #210 shipped — the live executor is at `backend/src/zebu/application/services/strategy_execution_service.py` (fully integrated, used by `StrategyActivation` flow). The future-tense framing was correct when written (Phase A), now misleading.
- **Why it matters**: An agent reading this assumes "the live executor doesn't exist yet" and may design a parallel one rather than extending the existing service.
- **Suggested fix**: Rewrite as `**Hot paths**: \`backend/src/zebu/application/services/backtest_executor.py\` (backtest loop) and \`backend/src/zebu/application/services/strategy_execution_service.py\` (live executor — mirrors the backtest loop's "iterate, generate signals, execute trades" shape). Both are canonical references for any new strategy-execution work.`

### [WARN-2] `architect.md:21-27` describes a target `docs/architecture/` schema with three subdirs that still don't exist

- **Where**:
  - `.claude/agents/architect.md:24` — `decisions/NNN-title.md    # ADRs (mkdir on first write)`
  - `.claude/agents/architect.md:26` — `domain/{entities,value-objects,services}.md  # (mkdir on first write)`
  - `.claude/agents/architect.md:27` — `api/contracts.md          # OpenAPI specs (mkdir on first write)`
  - `.claude/agents/architect.md:99` — `add an ADR under \`docs/architecture/decisions/NNN-title.md\``
  - `.claude/agents/frontend-swe.md:20` — `(the \`docs/architecture/api/\` shared-contracts directory is on the target schema but does not exist yet)`
- **Drift**: Real `docs/architecture/` contents: `archived/`, `authentication.md`, `phase-f-agent-in-the-loop.md` (new since 2026-05-09), `phase4-trading-strategies.md`, `principles.md`, `README.md`, `technical-boundaries.md`. None of `decisions/`, `domain/`, `api/` exist. This was WARN-2 in the 2026-05-09 sync — the architect.md schema was annotated with `mkdir on first write` notes (good — line 21 added the disclaimer) but no architect has actually triggered "first write" for any of the three subdirs in the intervening 4 months, suggesting they may not be needed in practice.
- **Why it matters**: Compounding: a 4-month-old "we'll create it when needed" that hasn't been needed is probably an aspirational layout that should either be retired or actually populated. Today's behaviour (line 99 telling an architect to write to a non-existent `decisions/NNN-title.md`) silently creates the parent on `mkdir -p` only — which leaves no precedent file for future ADRs to mirror.
- **Suggested fix**: Either (a) demote the schema block to "Target layout (not yet realized — when introducing a new ADR / domain spec / OpenAPI contract, create the subdir along with the first file)" and accept the `mkdir on first write` annotation as-is, or (b) seed each subdir with a single `README.md` describing its purpose so the layout is real. Option (a) is lower-effort.

### [WARN-3] `orchestrate-zebu` Wave-closeout section is isolated — `audit-mode` still describes worktree usage without referencing the closeout discipline

- **Where**:
  - `.claude/skills/orchestrate-zebu/SKILL.md:128-158` — full "Wave closeout — mandatory before the next dispatch" section (added during Phase J after H/I/E/F/G left 57 locked worktrees, 19 GB)
  - `.claude/skills/audit-mode/SKILL.md:224` — `**Worktree isolation.** Each audit agent should run in its own git worktree so one agent's read state never sees another's drafts. (\`git worktree add\` per agent; the agent writes to \`agent_docs/audits/\<DATE>/\<slug>.md\` directly.)`
- **Drift**: `audit-mode` is the other place worktrees are recommended, but it never points at the closeout discipline. An audit cycle (12 parallel agents in 2026-05-09) generates the same accumulation problem the closeout section was written to solve, but the audit-mode skill doesn't mention cleanup.
- **Why it matters**: A future audit cycle will leave the same debris pattern that motivated the orchestrate-zebu closeout. The two skills should cross-reference so the discipline applies wherever worktrees are spawned.
- **Suggested fix**: Add a one-line pointer at `.claude/skills/audit-mode/SKILL.md:225` (after the "Worktree isolation" bullet): `When the cycle closes, run the worktree cleanup steps in \`.claude/skills/orchestrate-zebu/SKILL.md\` §"Wave closeout".` No code change needed in the closeout section itself; it's already written generically enough.

### [WARN-4] `CLAUDE.md:88` describes `claude-infra-sync` as "run end-of-Phase" but `CLAUDE.md:109` says "end of each Wave / Phase" — inconsistent cadence guidance

- **Where**:
  - `CLAUDE.md:88` — `\`claude-infra-sync\` | Detect drift in \`CLAUDE.md\`/\`.claude/\` against the actual repo (run end-of-Phase) |`
  - `CLAUDE.md:109` — `**Run \`claude-infra-sync\` at the end of each Wave / Phase**: the skill at … audits CLAUDE.md + .claude/ for drift against the actual repo. Run it before the next agent dispatch cycle (or as the closeout of a Wave) and address BLOCKERs in the same PR.`
  - `.claude/skills/claude-infra-sync/SKILL.md:14` — `**End of every major Phase or Wave.**`
- **Drift**: Cadence is described three times with three slightly different framings ("end-of-Phase", "end of each Wave / Phase", "every major Phase or Wave"). The skill itself (line 14) is the authoritative version.
- **Why it matters**: An orchestrator unsure of cadence may run more or less often than intended. Phase J consisted of three waves and produced exactly one sync at the end — the looser "end-of-Phase" reading. If line 109's "end of each Wave / Phase" is taken literally, that's three runs.
- **Suggested fix**: Standardize on the skill's own wording (`At the end of every major Phase or Wave`) in both CLAUDE.md citations. CLAUDE.md:88 should read `(run end-of-Phase or end-of-Wave)`.

### [WARN-5] `claude-infra-sync` skill cites "React 18+ vs ^19.2.0" as a textbook case — the agent file is now correct, leftover from the original example state

- **Where**:
  - `.claude/skills/claude-infra-sync/SKILL.md:163` — `The 2026-05-09 audit's \`CLAUDE-P1-3\` (\`frontend-swe.md\` claimed "React 18+" while \`frontend/package.json\` is \`^19.2.0\`) was a textbook case. **Mismatch** = WARN.`
  - `.claude/skills/claude-infra-sync/SKILL.md:245` — `- Version claim mismatch (React 18+ vs \`^19.2.0\`).`
- **Drift**: `frontend-swe.md:12` now correctly says "React 19+". The skill text still uses the old broken state as the running example. The example is still useful pedagogically, but a reader checking "is React 18+ still the claim?" will be confused.
- **Why it matters**: Minor — the example is clearly framed as historical ("The 2026-05-09 audit's `CLAUDE-P1-3` …"). But repeating the broken state as "the textbook case" without noting it's fixed makes it harder to tell which examples in the skill are still-live patterns vs historical illustrations.
- **Suggested fix**: Add a parenthetical to line 163: `…was a textbook case (fixed in PR #229). **Mismatch** = WARN.` Same shape for line 245 if you want symmetry.

---

## NIT

### [NIT-1] `claude-infra-sync` skill's own example date is now generic `<YYYY-MM-DD>` — 2026-05-09 sync flagged a literal `2026-06-15`; today it's been generalized

- **Where**: `.claude/skills/claude-infra-sync/SKILL.md:330` — `**File path** of the report.`
- **Drift**: The placeholder is now correctly `<YYYY-MM-DD>` (generic), not a specific future date. This is **fixed** since the 2026-05-09 sync — flagging for the record so the next sync doesn't re-find it as drift.
- **Suggested fix**: None — listing this as a NIT to acknowledge the fix landed.

### [NIT-2] Three-place duplication of "next task number is N" persists even after BLOCKER-3 is fixed

- **Where**: see BLOCKER-3 for citations.
- **Drift**: The three-place duplication of "next task number" is its own meta-problem — the 2026-05-09 audit's `CLAUDE-P2-1` flagged this. Even after BLOCKER-3 is fixed, the duplication remains and will drift again.
- **Why it matters**: Mostly cosmetic; the duplication is what `claude-infra-sync` Pass 10 was designed to catch on every sync run.
- **Suggested fix**: After BLOCKER-3 is addressed, consider promoting `agent_docs/README.md` as the single source and replacing the citations in CLAUDE.md and `before-starting-work` with `(see \`agent_docs/README.md\` for the current next number)`. Defer to next docs-tidy.

### [NIT-3] PROGRESS.md hasn't been touched since Phase 4 (claims 1,142 tests, 831 backend / 311 frontend); no entries for Phases A–J

- **Where**:
  - `PROGRESS.md:9-19` — phase table tops out at "Phase 4: Trading Strategies ✅ Complete"
  - `PROGRESS.md:226` — `**Current State**: Production system live at zebutrader.com with weekend-aware caching, full trading strategy backtesting with comparison UI, and 1,142 tests. Ready for beta users!`
  - `PROGRESS.md:393` — `| Total Tests | 831 backend + 311 frontend = **1,142 tests** |`
  - `README.md:507-509` — same 1,142 tests claim
- **Drift**: PROGRESS.md is referenced by this skill (Pass 5) as the source of truth for test counts. It hasn't been updated since Phase 4 — Phases A through J added significant test coverage (Phase B audit fixes, Phase C live execution + API-key auth, Phase D MCP, Phase H/I/E/F/G triggers, Phase J data warmth). The actual test count is unknown without running `task quality:backend`/`:frontend` but is certainly far north of 1,142.
- **Why it matters**: Other places in the Claude infra defer to PROGRESS.md for truth. While drift on the count itself is a `docs-tidy` job, the bigger issue is that PROGRESS.md is structurally stuck in a pre-agent-platform-era.
- **Suggested fix**: `docs-tidy` pass to add a "Phase A–J: Agent Platform" entry summarizing the work. Out of scope for this sync; flagging for next docs-tidy.

### [NIT-4] `audit-mode/SKILL.md:8` references the 2026-05-09 audit as "the 12-dimension Phase B1 audit pass that demonstrated this pattern"

- **Where**: `.claude/skills/audit-mode/SKILL.md:8` — `Codifies how a specialist agent runs **as an auditor**: read code, produce a prioritized findings report, write **no code changes**. Distilled from the 2026-05-09 12-dimension Phase B1 audit pass that demonstrated this pattern.`
- **Drift**: The example is fine — it's an explicit historical reference. The framing reads naturally as past tense, so this is not actively misleading.
- **Suggested fix**: None — flagging in case a future audit cycle produces a new canonical reference; this should be updated then.

---

## Inventory snapshot

| Surface | Count | Notes |
|---|---:|---|
| Agents (`.claude/agents/`) | 7 | `architect`, `backend-swe`, `docs-refactorer`, `frontend-swe`, `qa`, `quality-infra`, `refactorer` |
| Skills (`.claude/skills/`) | 8 | `audit-mode`, `before-starting-work`, `claude-infra-sync`, `docs-tidy`, `e2e-qa-validation`, `git-workflow`, `orchestrate-zebu`, `quality-checks` |
| CLAUDE.md lines | 118 | (unchanged vs 2026-05-09) |
| Total Claude infra lines | 2,241 | up ~48 lines vs 2026-05-09 (orchestrate-zebu Wave-closeout section) |
| Backend Python | `>=3.13` (`pyproject.toml`) | matches agent files |
| Frontend React | `^19.2.0` (`package.json`) | matches `frontend-swe.md:12` |
| Latest task | `213_queue_mode_triggers.md` | next = **214** |
| Most recent progress doc | `2026-05-13_03-40-33_phase-j-data-warmth-and-pattern-b.md` | |

CLAUDE.md skills table ↔ `.claude/skills/` disk: 1:1 match (8/8). CLAUDE.md agents table ↔ `.claude/agents/` disk: 1:1 match (7/7). No orphaned or missing entries on either side.

## Passes run / skipped

- Pass 1 (stale paths) — all 24 backtick-quoted file references resolve; all 30 directory-shaped references resolve except the 3 aspirational subdirs under `docs/architecture/` (covered by WARN-2).
- Pass 2 (cross-references) — all skill / agent references resolve.
- Pass 3 (skills inventory) — clean.
- Pass 4 (agents inventory) — clean.
- Pass 5 (test-count freshness) — see NIT-3.
- Pass 6 (framework versions) — clean (React 19+, Python 3.13+, both backed by lock files).
- Pass 7 (endpoint references) — `POST /api/v1/api-keys` mentioned in `CLAUDE.md:105` resolves to `api_keys_router` mounted at `main.py:178`.
- Pass 8 (removed concepts) — Phase J's new domain concepts (`JobExecution`, `BackfillTask`, `TriggerInvocationMode`, `HistoricalDataPrewarmer`, `IncompleteHistoricalDataError`, `@with_job_audit`) all exist in code; CLAUDE.md doesn't mention them but the existing inventory (`ExplorationTask`, `StrategyConditionTrigger`) is correctly present. No orphan concepts found. Whether to add the Phase J concepts to CLAUDE.md is a judgment call — they're more "implementation detail of the observability/data-warmth subsystems" than "load-bearing nouns an agent needs at dispatch time"; leaving them out is defensible.
- Pass 9 (terminology) — `sub-agent` is now gone (was WARN-1 in 2026-05-09). `specialist agent` is consistently used; `subagent_type` is the literal API param (correct).
- Pass 10 (single-source-of-truth) — see BLOCKER-3.

## Recommended follow-up

- **BLOCKER-1, -2, -3 → fix before next agent dispatch**. All three are in `CLAUDE.md` (and BLOCKER-3 also touches `agent_docs/README.md` + `before-starting-work`). Fix in one `docs-refactorer` PR titled `fix(claude-infra): resolve Phase-J drift from 2026-05-13 sync`. The three changes are tightly scoped — ~30 lines total across 3 files.
- **WARN-1, -2, -3, -4, -5 → bundle into the next docs-tidy pass** or fold into the BLOCKER-fix PR if the change overhead is low (WARN-1 is a one-line edit, WARN-3 is a one-line cross-reference).
- **NIT-3 (PROGRESS.md staleness) → next docs-tidy after the BLOCKER fix lands**. Larger scope; deserves its own focus.
- NIT-1, -2, -4 → defer.

## Calibration cross-check

- 3 BLOCKERs, 5 WARNs, 4 NITs = 12 findings. Within the 5–20 target band.
- Each BLOCKER fails the "would I bother Tim about this on a Sunday?" test in the right direction: an agent dispatched against today's CLAUDE.md will materially misroute (BLOCKER-1), design code that ignores the existing auth path (BLOCKER-2), or fail to write a task spec (BLOCKER-3).
- WARNs are real drift, fixable in a focused PR, not actively breaking.
- NITs are kept at 4 — pruned aggressively (NIT-1 acknowledges a fix; NIT-3 is the only one with real follow-up scope, deferred to docs-tidy).
- No `auto-fix` action taken. No code touched. Only file written: this report.
