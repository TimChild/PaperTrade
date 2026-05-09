"""add_strategy_activations

Creates the ``strategy_activations`` table with foreign keys to ``strategies``
and ``portfolios``. Both FKs use ``ON DELETE CASCADE`` — an activation has
no purpose once either its strategy or its target portfolio is gone.

Naming and idempotency conventions follow Alembic ``b002add_strategy_and_backtest``
(table-creation pattern with ``_has_table`` / ``_has_index`` guards) and
Alembic ``d26cec7cdf69`` from PR #224 (FK constraints with explicit cascade
rules and ``fk_<table>_<column>_<parent>`` naming).

User-id columns intentionally have NO foreign key — users live in Clerk
(external auth provider); there is no ``users`` table in this schema.

Revision ID: a7117ef792cb
Revises: b002add_strategy_and_backtest
Create Date: 2026-05-09 18:16:17.487765

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7117ef792cb"
down_revision: str | Sequence[str] | None = "b002add_strategy_and_backtest"
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
    """Create the ``strategy_activations`` table and supporting indexes."""
    if not _has_table("strategy_activations"):
        op.create_table(
            "strategy_activations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("strategy_id", sa.Uuid(), nullable=False),
            sa.Column("portfolio_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("frequency", sa.String(length=30), nullable=False),
            sa.Column("last_executed_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["strategy_id"],
                ["strategies.id"],
                name="fk_strategy_activations_strategy_id_strategies",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["portfolio_id"],
                ["portfolios.id"],
                name="fk_strategy_activations_portfolio_id_portfolios",
                ondelete="CASCADE",
            ),
        )

    # Composite index supports list_for_user filtered by status (the API's
    # most-common query pattern: "show me my active strategies").
    if not _has_index("strategy_activations", "idx_strategy_activation_user_status"):
        op.create_index(
            "idx_strategy_activation_user_status",
            "strategy_activations",
            ["user_id", "status"],
        )

    if not _has_index("strategy_activations", "idx_strategy_activation_strategy_id"):
        op.create_index(
            "idx_strategy_activation_strategy_id",
            "strategy_activations",
            ["strategy_id"],
        )

    if not _has_index("strategy_activations", "idx_strategy_activation_portfolio_id"):
        op.create_index(
            "idx_strategy_activation_portfolio_id",
            "strategy_activations",
            ["portfolio_id"],
        )


def downgrade() -> None:
    """Drop the ``strategy_activations`` table and its indexes."""
    if _has_index("strategy_activations", "idx_strategy_activation_portfolio_id"):
        op.drop_index(
            "idx_strategy_activation_portfolio_id",
            table_name="strategy_activations",
        )
    if _has_index("strategy_activations", "idx_strategy_activation_strategy_id"):
        op.drop_index(
            "idx_strategy_activation_strategy_id",
            table_name="strategy_activations",
        )
    if _has_index("strategy_activations", "idx_strategy_activation_user_status"):
        op.drop_index(
            "idx_strategy_activation_user_status",
            table_name="strategy_activations",
        )
    if _has_table("strategy_activations"):
        op.drop_table("strategy_activations")
