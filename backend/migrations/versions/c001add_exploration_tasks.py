"""add_exploration_tasks_table

Revision ID: c001add_exploration_tasks
Revises: a7117ef792cb
Create Date: 2026-05-09

Phase C4 — adds the ``exploration_tasks`` table for the agent-platform
queue. Humans create tasks; agents claim and work them. See
``docs/planning/agent-platform-proposal.md`` §3.4 / §4 / Phase C4 for the
domain context.

The composite index on ``(status, created_at)`` is what the queue relies
on for the "next OPEN task" query.

The ``target_portfolio_id`` foreign key uses ``ON DELETE SET NULL`` so a
task whose target portfolio is deleted survives but loses its portfolio
binding. ``created_by`` deliberately has no FK — users live in Clerk.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c001add_exploration_tasks"
down_revision: str | Sequence[str] | None = "a7117ef792cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    """Create exploration_tasks table."""
    if not _has_table("exploration_tasks"):
        op.create_table(
            "exploration_tasks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("prompt", sa.String(length=4000), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("target_portfolio_id", sa.Uuid(), nullable=True),
            sa.Column("tickers", sa.JSON(), nullable=True),
            sa.Column("constraints", sa.JSON(), nullable=True),
            sa.Column("claimed_by", sa.String(length=200), nullable=True),
            sa.Column("claimed_at", sa.DateTime(), nullable=True),
            sa.Column("findings", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["target_portfolio_id"],
                ["portfolios.id"],
                name="fk_exploration_task_portfolio",
                ondelete="SET NULL",
            ),
        )

    if not _has_index("exploration_tasks", "idx_exploration_task_status_created"):
        op.create_index(
            "idx_exploration_task_status_created",
            "exploration_tasks",
            ["status", "created_at"],
        )

    if not _has_index("exploration_tasks", "idx_exploration_task_created_by"):
        op.create_index(
            "idx_exploration_task_created_by",
            "exploration_tasks",
            ["created_by"],
        )

    if not _has_index("exploration_tasks", "idx_exploration_task_portfolio_id"):
        op.create_index(
            "idx_exploration_task_portfolio_id",
            "exploration_tasks",
            ["target_portfolio_id"],
        )


def downgrade() -> None:
    """Drop exploration_tasks table.

    Drops indexes first, then the table itself. The FK constraint is
    dropped implicitly when the table is dropped — SQLite cannot ALTER a
    constraint, so we don't try to drop it explicitly. PostgreSQL likewise
    drops dependent constraints when the table goes.
    """
    if _has_index("exploration_tasks", "idx_exploration_task_portfolio_id"):
        op.drop_index(
            "idx_exploration_task_portfolio_id",
            table_name="exploration_tasks",
        )
    if _has_index("exploration_tasks", "idx_exploration_task_created_by"):
        op.drop_index(
            "idx_exploration_task_created_by",
            table_name="exploration_tasks",
        )
    if _has_index("exploration_tasks", "idx_exploration_task_status_created"):
        op.drop_index(
            "idx_exploration_task_status_created",
            table_name="exploration_tasks",
        )
    if _has_table("exploration_tasks"):
        op.drop_table("exploration_tasks")
