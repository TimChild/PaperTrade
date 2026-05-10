"""ExplorationTask read tools.

These wrap the Phase C4 ``ExplorationTask`` queue endpoints so agents can
inspect the human-queued backlog without yet being able to claim or
finish tasks (those are Wave 2 write tools).
"""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import ExplorationTask, Page


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
