"""add_strategy_and_backtest_tables

Revision ID: b002add_strategy_and_backtest
Revises: b001add_portfolio_type
Create Date: 2026-03-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b002add_strategy_and_backtest"
down_revision: str | Sequence[str] | None = "b001add_portfolio_type"
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
    """Create strategies and backtest_runs tables."""
    if not _has_table("strategies"):
        op.create_table(
            "strategies",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("strategy_type", sa.String(length=50), nullable=False),
            sa.Column("tickers", sa.JSON(), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("strategies", "idx_strategy_user_id"):
        op.create_index("idx_strategy_user_id", "strategies", ["user_id"])

    if not _has_table("backtest_runs"):
        op.create_table(
            "backtest_runs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("strategy_id", sa.Uuid(), nullable=True),
            sa.Column("portfolio_id", sa.Uuid(), nullable=False),
            sa.Column("strategy_snapshot", sa.JSON(), nullable=False),
            sa.Column("backtest_name", sa.String(length=100), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column(
                "initial_cash",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
            ),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column(
                "total_return_pct",
                sa.Numeric(precision=15, scale=4),
                nullable=True,
            ),
            sa.Column(
                "max_drawdown_pct",
                sa.Numeric(precision=15, scale=4),
                nullable=True,
            ),
            sa.Column(
                "annualized_return_pct",
                sa.Numeric(precision=15, scale=4),
                nullable=True,
            ),
            sa.Column("total_trades", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("backtest_runs", "idx_backtest_run_user_id"):
        op.create_index("idx_backtest_run_user_id", "backtest_runs", ["user_id"])
    if not _has_index("backtest_runs", "idx_backtest_run_portfolio_id"):
        op.create_index(
            "idx_backtest_run_portfolio_id", "backtest_runs", ["portfolio_id"]
        )
    if not _has_index("backtest_runs", "idx_backtest_run_strategy_id"):
        op.create_index(
            "idx_backtest_run_strategy_id", "backtest_runs", ["strategy_id"]
        )


def downgrade() -> None:
    """Drop strategies and backtest_runs tables."""
    if _has_index("backtest_runs", "idx_backtest_run_strategy_id"):
        op.drop_index("idx_backtest_run_strategy_id", table_name="backtest_runs")
    if _has_index("backtest_runs", "idx_backtest_run_portfolio_id"):
        op.drop_index("idx_backtest_run_portfolio_id", table_name="backtest_runs")
    if _has_index("backtest_runs", "idx_backtest_run_user_id"):
        op.drop_index("idx_backtest_run_user_id", table_name="backtest_runs")
    if _has_table("backtest_runs"):
        op.drop_table("backtest_runs")

    if _has_index("strategies", "idx_strategy_user_id"):
        op.drop_index("idx_strategy_user_id", table_name="strategies")
    if _has_table("strategies"):
        op.drop_table("strategies")
