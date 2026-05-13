"""TriggerInvocationMode value object — how a fired trigger reaches an agent.

Phase J (Task #213) introduces **Pattern B** for trigger invocation. Prior
to this phase, every fired trigger went through the inline Anthropic
Messages API path (Pattern A — see Phase F design §3). The new mode flag
distinguishes between:

* ``DIRECT`` — the existing F-3 behavior: the
  :class:`TriggerInvocationOrchestrator` calls the configured
  :class:`AgentInvocationPort` (Anthropic Haiku in production) inline and
  acts on the structured decision (BUY / SELL / HOLD / MODIFY_STRATEGY /
  NEEDS_HUMAN) before returning.
* ``QUEUE`` — Pattern B: instead of invoking an agent inline, the
  orchestrator files an URGENT :class:`ExplorationTask`. The user's
  desktop Claude / Gemini CLI / any MCP-aware client polls the
  exploration-task queue (via ``mcp__zebu__list_exploration_tasks``) and
  processes the task with whatever connectors and tools that client has
  already authenticated against.

Defaults to ``DIRECT`` on the entity so existing rows behave exactly as
they did pre-Phase-J. New triggers may opt into ``QUEUE`` per-row via
the API ``mode`` field.

Stored as a string in the DB (matches the pattern used by
:class:`TriggerStatus`, :class:`ConditionType`, and other lifecycle
enums in this package).
"""

from enum import StrEnum


class TriggerInvocationMode(StrEnum):
    """How a fired trigger reaches the agent.

    Values:
        DIRECT: Inline platform invocation. The orchestrator calls the
            configured :class:`AgentInvocationPort` adapter (Anthropic
            Haiku in production) synchronously and acts on the returned
            decision before persisting the audit row. Low latency, no
            human-in-loop. Matches the existing Phase F-3 behavior.
        QUEUE: Files an URGENT :class:`ExplorationTask` for an out-of-band
            agent (desktop Claude, Gemini CLI, etc.) to claim and
            process. The trigger's :class:`TriggerFireRecord` is still
            written so the activity feed stays coherent — it records
            that the trigger fired and enqueued a task. Used when the
            operator wants the wider toolset of their own desktop agent
            rather than the platform's inline Haiku adapter.
    """

    DIRECT = "direct"
    QUEUE = "queue"
