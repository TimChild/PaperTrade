# Task 213 — Pattern B queue-mode triggers (Phase J — multi-provider)

**Status**: Scoped, not started
**Branch**: `feat/j-queue-mode-triggers`
**Agent**: `backend-swe` + `frontend-swe` (single PR, full-stack — change is small)

## Overview

Today, when a `StrategyConditionTrigger` fires, the `TriggerInvocationOrchestrator` always calls the Anthropic Messages API inline (Pattern A in `docs/planning/agent-platform-next-steps.md` §2.2). This task adds **Pattern B**: a `mode` flag on the trigger entity that, when set to `QUEUE`, causes the orchestrator to file an `[URGENT]`-labelled `ExplorationTask` instead of calling Anthropic. The user's desktop Claude / Gemini CLI / any MCP-aware client can then poll the ExplorationTask queue (via `mcp__zebu__list_exploration_tasks` or the equivalent REST endpoint) and process the urgent task using whichever connectors and tools that client already has wired (Brave Search, Tavily, Gmail, Drive, etc.).

**Why this beats building a Gemini direct-API adapter first**: Pattern B reuses every connector the user has already authenticated against in their desktop agent. No new provider integration, no new auth surface, no new error-handling shape. It's the cheapest path to "trigger fires can reach my preferred agent client."

Origin: `docs/planning/agent-platform-next-steps.md` §2.2 ("Pattern B — File urgent ExplorationTask → poll-and-claim") and §2.3 ("Pattern B first — biggest leverage for least work").

## Architecture

### Domain change

`StrategyConditionTrigger` (`backend/src/zebu/domain/entities/strategy_condition_trigger.py`) gains a new field:

```python
mode: TriggerInvocationMode = TriggerInvocationMode.DIRECT
```

New value object `TriggerInvocationMode` (`backend/src/zebu/domain/value_objects/trigger_invocation_mode.py`):

```python
class TriggerInvocationMode(StrEnum):
    DIRECT = "direct"  # Inline Anthropic call (current F-3 behavior)
    QUEUE = "queue"    # File an URGENT ExplorationTask
```

Defaults to `DIRECT` for backwards compatibility — existing rows behave exactly as today.

The choice of `StrEnum` matches the existing `TriggerStatus` / `ConditionType` patterns and serialises cleanly via the API schemas.

### Migration

`j003_trigger_mode` adds a `mode VARCHAR(16) NOT NULL DEFAULT 'direct'` column to `strategy_condition_triggers`. No backfill needed — the default covers all existing rows.

### Orchestrator change

`TriggerInvocationOrchestrator.fire()` (`backend/src/zebu/application/services/trigger_invocation_orchestrator.py:219`) branches on `trigger.mode`:

- `DIRECT` — current behavior (call `agent_invocation.invoke(...)`, persist `TriggerFireRecord`).
- `QUEUE` — call a new collaborator `_file_urgent_exploration_task(trigger, evaluation, ...)`, which builds the task title + description from the trigger's `agent_prompt` and the condition's evaluation data, then calls `exploration_task_repo.create(...)` with `claimed_by=None`, `status=OPEN`, and a leading `[URGENT]` prefix on the title (the existing convention for high-priority queue items per the operating manual).

The `TriggerFireRecord` audit row is written in both modes — the `mode` field records which path was taken, and `agent_response` is either the Anthropic JSON (DIRECT) or `{"queued_task_id": "<uuid>"}` (QUEUE). This keeps the activity feed coherent.

### Schema + endpoint changes

- `POST /api/v1/triggers` request schema accepts an optional `mode` field (default `"direct"`).
- `GET /api/v1/triggers/{id}` response includes `mode`.
- `PATCH /api/v1/triggers/{id}` allows `mode` to be updated (status-transition rules unchanged).
- OpenAPI docstrings + the schema in `adapters/inbound/api/schemas/triggers.py` updated.

### Frontend change

In the trigger creation / edit form (`frontend/src/components/features/triggers/TriggerForm.tsx` or wherever the existing form lives — agent should confirm):

- Radio group: "Invocation mode"
  - **Direct (Anthropic Haiku)** — *Default. The platform calls the agent inline. Low latency, no human-in-loop.*
  - **Queue (Desktop Claude / Gemini CLI)** — *Files an URGENT task. Your desktop agent polls and processes it with its own connectors.*

Wire through the existing TanStack mutation; no new API client work beyond the schema field.

In the fire log view, show a small pill: "Inline" or "Queued" so the user can tell at a glance which path each fire took.

### Operating manual update

`docs/agents/operating-manual.md` §3.5 (or wherever trigger configuration is documented) gains a short subsection explaining the two modes, when to pick each, and how to consume queued tasks (polling cadence, `mcp__zebu__claim_exploration_task` workflow).

## Implementation plan

Single PR. Order within the branch:

1. **Domain VO** `TriggerInvocationMode` + unit test.
2. **Entity** `StrategyConditionTrigger` — add `mode` field, default `DIRECT`. Update existing constructor tests if they assert on the field set.
3. **Migration** `j003_trigger_mode`.
4. **SQL model + repository** — add column, plumb through `to_domain` / `from_domain`. In-memory variant updated for protocol compatibility.
5. **Orchestrator** — branch on `mode`. Extract `_file_urgent_exploration_task` helper.
6. **API schemas** — request / response include `mode`. Validation on POST + PATCH.
7. **Frontend** — radio in form, pill in fire log, types updated.
8. **Operating manual** — short subsection.
9. **Integration test** — full path: create QUEUE trigger → simulate fire → ExplorationTask appears with `[URGENT]` prefix → claim it via MCP → submit finding → finding persisted.

## Testing strategy

**Unit**:

- `TriggerInvocationMode` enum semantics.
- `StrategyConditionTrigger` accepts `mode` (default + explicit), invariants unchanged.
- Orchestrator branches correctly: mock the `agent_invocation` port and the `exploration_task_repo` port; assert one is called and the other is not, per mode.
- Audit row is written in both modes (`TriggerFireRecord` exists with the right `mode` field).

**Integration**:

- `POST /triggers { mode: "queue" }` → 201 with `mode=queue`.
- `POST /triggers` without mode → 201 with `mode=direct` (default).
- `PATCH /triggers/{id} { mode: "queue" }` → 200, persisted, next fire takes queue path.
- Full pipeline: queue-mode trigger fires (via the smoke-test pattern) → `ExplorationTask` row exists with `[URGENT]` prefix.

**Frontend component**:

- Radio renders, default is "Direct", switching updates the mutation payload.
- Fire log pill renders "Inline" / "Queued" per record.

## Success criteria

- `task ci` green.
- An existing DIRECT trigger continues to behave identically (no observed change in latency, audit shape, fire-record contents).
- A new QUEUE trigger fires → an URGENT ExplorationTask appears in the queue within one scheduler tick.
- The user can claim that task from Claude Desktop / Claude Code / Gemini CLI using the existing MCP tools — no new MCP work required.
- Operating manual documents both modes.

## Open question — Q1 from agent-platform-next-steps.md §5

> Should queue-mode triggers also call the inline Anthropic adapter as fallback if no one claims within N minutes?

**Default position adopted here**: no fallback. Modes are distinct. Reconsider only if urgent tasks are observed getting starved (low priority follow-up; not in scope of this PR).

## Out of scope

- Pattern C (Gemini direct-API adapter) — separate task, requires `GOOGLE_API_KEY` provisioning.
- Auto-promotion ("queue then fall back to direct after N minutes") — see open question above.
- Notification when an URGENT task lands (desktop notification, Slack ping) — depends on per-user notification infra not built yet.
- Multi-recipient queue (route to specific user's desktop agent) — single-user system right now; revisit when multi-tenant.

## References

- `docs/planning/agent-platform-next-steps.md` §2.2, §2.3 (Pattern B motivation + recommended sequencing)
- `docs/architecture/phase-f-agent-in-the-loop.md` (F-3 Anthropic-only invocation flow that this task generalises)
- `backend/src/zebu/application/services/trigger_invocation_orchestrator.py:154` — orchestrator entry point
- `backend/src/zebu/domain/entities/strategy_condition_trigger.py:52` — trigger entity to extend
- `mcp/` — Zebu MCP server, already exposes `list_exploration_tasks` / `claim_exploration_task` / `submit_exploration_finding` for the consumer side
- `docs/agents/operating-manual.md` — to extend with §3.5 subsection
