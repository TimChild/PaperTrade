"""ExplorationTask read + queue-management tools.

Wraps the Phase C4 ``ExplorationTask`` queue endpoints. Wave 1 added the
read tools; Wave 2 adds create / claim / submit-findings / abandon plus
the local-only ``note`` tool.
"""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import (
    ClaimExplorationTaskRequest,
    CreateExplorationTaskRequest,
    ExplorationConstraints,
    ExplorationTask,
    NoteResult,
    Page,
    SubmitExplorationFindingsRequest,
)


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register exploration tools on ``server``."""

    @server.tool(
        name="list_exploration_tasks",
        description=(
            "List exploration tasks (the human → agent task queue). By "
            "default returns OPEN tasks across all users — the claimable "
            "backlog. Pass status='IN_PROGRESS', 'DONE', or 'ABANDONED' to "
            "narrow further. Pass scope='mine' to restrict to tasks the "
            "current user created. Use this on agent wake-up to find "
            "something to work on."
        ),
    )
    async def list_exploration_tasks(
        status: str | None = None,
        scope: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> Page[ExplorationTask]:
        """List exploration tasks."""
        return await client.list_exploration_tasks(
            status=status,
            scope=scope,
            limit=limit,
            offset=offset,
        )

    @server.tool(
        name="get_exploration_task",
        description=(
            "Get a single exploration task by ID. Returns the full task: "
            "prompt (the user's free-form request), status, optional "
            "tickers / target_portfolio_id, optional constraints "
            "(max_backtests, allow_live_activation, "
            "strategy_type_whitelist), and any submitted findings."
        ),
    )
    async def get_exploration_task(task_id: UUID) -> ExplorationTask:
        """Get a single exploration task."""
        return await client.get_exploration_task(task_id)

    @server.tool(
        name="create_exploration_task",
        description=(
            "File a new exploration task on the human → agent queue. "
            "Typically used by humans through the GUI, but agents can also "
            "file sub-tasks for other agents. The prompt is the only "
            "required field. constraints accepts an object with optional "
            "max_backtests (int>0), allow_live_activation (bool, default "
            "true), and strategy_type_whitelist (list of strategy types). "
            "The created task starts in OPEN status, ready to be claimed."
        ),
    )
    async def create_exploration_task(
        prompt: str,
        target_portfolio_id: UUID | None = None,
        tickers: list[str] | None = None,
        constraints: ExplorationConstraints | None = None,
    ) -> ExplorationTask:
        """File a new exploration task."""
        request = CreateExplorationTaskRequest(
            prompt=prompt,
            target_portfolio_id=target_portfolio_id,
            tickers=tickers,
            constraints=constraints,
        )
        return await client.create_exploration_task(request)

    @server.tool(
        name="claim_exploration_task",
        description=(
            "Atomically claim an OPEN exploration task. Race-safe: the "
            "backend issues a status-conditional UPDATE so two callers "
            "fighting for the same task can't both win. Optionally pass "
            "agent_id (free-form label, e.g. the API-key label) for audit "
            "visibility — defaults to the auth user's UUID.\n\n"
            "Returns 404 if the task doesn't exist; 409 if it's no longer "
            "OPEN (someone else claimed it, or it's already DONE / "
            "ABANDONED). The core agent intake — call this on wake-up "
            "after list_exploration_tasks finds something to work on."
        ),
    )
    async def claim_exploration_task(
        task_id: UUID,
        agent_id: str | None = None,
    ) -> ExplorationTask:
        """Atomically claim an OPEN exploration task."""
        request = ClaimExplorationTaskRequest(agent_id=agent_id)
        return await client.claim_exploration_task(task_id, request)

    @server.tool(
        name="submit_exploration_finding",
        description=(
            "Submit findings for a claimed task and DONE-transition it. "
            "summary is required; backtest_run_ids and strategy_ids "
            "reference work the agent produced; notes is a free-form list "
            "of additional commentary. The task must currently be in "
            "IN_PROGRESS status — submitting against an OPEN / DONE / "
            "ABANDONED task returns 409."
        ),
    )
    async def submit_exploration_finding(
        task_id: UUID,
        summary: str,
        backtest_run_ids: list[UUID] | None = None,
        strategy_ids: list[UUID] | None = None,
        notes: list[str] | None = None,
    ) -> ExplorationTask:
        """Submit findings + DONE-transition a claimed task."""
        request = SubmitExplorationFindingsRequest(
            summary=summary,
            backtest_run_ids=backtest_run_ids or [],
            strategy_ids=strategy_ids or [],
            notes=notes,
        )
        return await client.submit_exploration_findings(task_id, request)

    @server.tool(
        name="abandon_exploration_task",
        description=(
            "Abandon and delete an exploration task. Note the backend's "
            "rule: only the task's *creator* (created_by) may delete it — "
            "a claiming agent that gives up does not currently have a "
            "first-class abandon path. If you're the creator and want to "
            "cancel an unclaimed or in-progress task, this is the right "
            "tool. If you're a claiming agent that needs to give up, "
            "submit a finding with notes explaining the abandonment "
            "instead, or surface to a human.\n\n"
            "Returns 204 (no content) on success; raises with 403 if the "
            "caller isn't the task's creator."
        ),
    )
    async def abandon_exploration_task(task_id: UUID) -> dict[str, object]:
        """Delete an exploration task (creator-only)."""
        await client.delete_exploration_task(task_id)
        # Tools must return a structured payload; a small ack is more
        # useful to the agent than ``None`` (which most MCP clients
        # render as an empty result).
        return {"task_id": str(task_id), "deleted": True}

    @server.tool(
        name="note",
        description=(
            "Record a free-form note. Local-only in Wave 2: the backend "
            "has no free-floating note endpoint, and submitting findings "
            "for an exploration task DONE-transitions it (so it can't be "
            "used as an append-only thought channel without ending the "
            "task). The tool echoes the note back with guidance on the "
            "persistent paths.\n\n"
            "When exploration_task_id is supplied, the recommended next "
            "step is submit_exploration_finding (which accepts a notes "
            "list and DONE-transitions the task when you're ready to "
            "wrap up). When strategy_id is supplied, persistent context "
            "for that strategy can be added by filing a new "
            "exploration_task referencing the strategy in its prompt."
        ),
    )
    async def note(
        text: str,
        exploration_task_id: UUID | None = None,
        strategy_id: UUID | None = None,
    ) -> NoteResult:
        """Record a free-form note (local-only)."""
        if exploration_task_id is not None:
            advice = (
                "To persist this note, call submit_exploration_finding "
                f"on task {exploration_task_id} when you're ready to "
                "DONE-transition it (the notes list accepts free-form "
                "strings)."
            )
        elif strategy_id is not None:
            advice = (
                "To persist context about a strategy, file a new "
                "exploration_task referencing the strategy in its prompt "
                "(or include the note in a forthcoming "
                "submit_exploration_finding call)."
            )
        else:
            advice = (
                "To persist a note, first create an exploration_task "
                "(create_exploration_task) and then submit findings "
                "against it when you're done."
            )
        return NoteResult(
            text=text,
            exploration_task_id=exploration_task_id,
            strategy_id=strategy_id,
            persisted=False,
            advice=advice,
        )
