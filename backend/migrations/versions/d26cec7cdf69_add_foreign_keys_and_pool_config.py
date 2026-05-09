"""add_foreign_keys_and_pool_config

Adds foreign-key constraints across the schema, a unique constraint on
``portfolio_snapshots(portfolio_id, snapshot_date)``, and (for documentation
only — engine-side change is in ``infrastructure/database.py``) the pool
configuration to support reliable Postgres connections.

FK summary:

- ``transactions.portfolio_id`` -> ``portfolios.id`` ON DELETE CASCADE
- ``portfolio_snapshots.portfolio_id`` -> ``portfolios.id`` ON DELETE CASCADE
- ``backtest_runs.portfolio_id`` -> ``portfolios.id`` ON DELETE CASCADE
- ``backtest_runs.strategy_id`` -> ``strategies.id`` ON DELETE SET NULL

User-id columns intentionally have NO foreign key — users live in Clerk
(external auth provider); there is no ``users`` table in this schema.

Pre-flight orphan audit:

The migration will COUNT orphan rows for each FK before adding the
constraint. If any are found in dev/staging, the migration logs them and
fails fast with an actionable message. Production deploys must be preceded
by an orphan check on the prod DB (see PR description).

Revision ID: d26cec7cdf69
Revises: b002add_strategy_and_backtest
Create Date: 2026-05-09 12:47:50.778481

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d26cec7cdf69"
down_revision: str | Sequence[str] | None = "b002add_strategy_and_backtest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


logger = logging.getLogger("alembic.runtime.migration")


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_fk(table_name: str, fk_name: str) -> bool:
    if not _has_table(table_name):
        return False
    fks = _inspector().get_foreign_keys(table_name)
    return any(fk.get("name") == fk_name for fk in fks)


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    uniques = _inspector().get_unique_constraints(table_name)
    return any(uq.get("name") == constraint_name for uq in uniques)


def _count_orphans(
    bind: sa.Connection,
    child_table: str,
    child_column: str,
    parent_table: str,
    parent_column: str = "id",
    *,
    allow_null: bool = False,
) -> int:
    """Count rows in ``child_table`` whose ``child_column`` does not match
    any row in ``parent_table``. NULLs are excluded when ``allow_null`` is True.
    """
    null_clause = f"AND c.{child_column} IS NOT NULL" if allow_null else ""
    sql = sa.text(
        f"""
        SELECT COUNT(*)
        FROM {child_table} c
        LEFT JOIN {parent_table} p
          ON c.{child_column} = p.{parent_column}
        WHERE p.{parent_column} IS NULL
          {null_clause}
        """
    )
    result = bind.execute(sql).scalar()
    return int(result or 0)


def _audit_orphans(bind: sa.Connection) -> None:
    """Audit existing data for orphan rows that would violate the new FKs.

    Logs each FK's orphan count. Raises if any orphans exist so that we
    abort the migration with a clear error rather than failing later in
    the constraint creation with a less actionable database-level error.
    """
    audits: list[tuple[str, str, str, bool]] = [
        ("transactions", "portfolio_id", "portfolios", False),
        ("portfolio_snapshots", "portfolio_id", "portfolios", False),
        ("backtest_runs", "portfolio_id", "portfolios", False),
        ("backtest_runs", "strategy_id", "strategies", True),
    ]

    found_orphans: list[str] = []
    for child_table, child_column, parent_table, allow_null in audits:
        if not _has_table(child_table) or not _has_table(parent_table):
            # Table doesn't exist yet (fresh DB) — nothing to audit.
            continue
        orphan_count = _count_orphans(
            bind,
            child_table,
            child_column,
            parent_table,
            allow_null=allow_null,
        )
        msg = (
            f"orphan-audit {child_table}.{child_column} -> "
            f"{parent_table}.id: {orphan_count} orphan rows"
        )
        if orphan_count > 0:
            logger.error(msg)
            found_orphans.append(f"{child_table}.{child_column}={orphan_count}")
        else:
            logger.info(msg)

    if found_orphans:
        raise RuntimeError(
            "Cannot add foreign-key constraints: orphan rows present in "
            "the database. Counts: " + ", ".join(found_orphans) + ". "
            "Clean these up before re-running the migration. See PR for "
            "guidance on prod cleanup."
        )


def upgrade() -> None:
    """Add FK constraints and unique constraint."""
    bind = op.get_bind()

    # 1. Orphan audit — fail fast if any cross-table id points nowhere.
    _audit_orphans(bind)

    # 2. Foreign-key constraints.
    #
    # SQLite cannot ALTER an existing table to add a foreign key, so we
    # use batch_alter_table() which transparently does a CREATE+COPY+DROP
    # rebuild on SQLite and a regular ALTER on Postgres.

    # transactions.portfolio_id -> portfolios.id (CASCADE)
    if _has_table("transactions") and not _has_fk(
        "transactions", "fk_transactions_portfolio_id_portfolios"
    ):
        with op.batch_alter_table("transactions") as batch:
            batch.create_foreign_key(
                "fk_transactions_portfolio_id_portfolios",
                "portfolios",
                ["portfolio_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # portfolio_snapshots.portfolio_id -> portfolios.id (CASCADE)
    if _has_table("portfolio_snapshots") and not _has_fk(
        "portfolio_snapshots", "fk_portfolio_snapshots_portfolio_id_portfolios"
    ):
        with op.batch_alter_table("portfolio_snapshots") as batch:
            batch.create_foreign_key(
                "fk_portfolio_snapshots_portfolio_id_portfolios",
                "portfolios",
                ["portfolio_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # portfolio_snapshots: unique constraint on (portfolio_id, snapshot_date)
    if _has_table("portfolio_snapshots") and not _has_unique_constraint(
        "portfolio_snapshots", "uq_snapshot_portfolio_date"
    ):
        with op.batch_alter_table("portfolio_snapshots") as batch:
            batch.create_unique_constraint(
                "uq_snapshot_portfolio_date",
                ["portfolio_id", "snapshot_date"],
            )

    # backtest_runs.portfolio_id -> portfolios.id (CASCADE)
    if _has_table("backtest_runs") and not _has_fk(
        "backtest_runs", "fk_backtest_runs_portfolio_id_portfolios"
    ):
        with op.batch_alter_table("backtest_runs") as batch:
            batch.create_foreign_key(
                "fk_backtest_runs_portfolio_id_portfolios",
                "portfolios",
                ["portfolio_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # backtest_runs.strategy_id -> strategies.id (SET NULL — soft reference)
    if _has_table("backtest_runs") and not _has_fk(
        "backtest_runs", "fk_backtest_runs_strategy_id_strategies"
    ):
        with op.batch_alter_table("backtest_runs") as batch:
            batch.create_foreign_key(
                "fk_backtest_runs_strategy_id_strategies",
                "strategies",
                ["strategy_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    """Drop FK constraints and unique constraint."""
    if _has_fk("backtest_runs", "fk_backtest_runs_strategy_id_strategies"):
        with op.batch_alter_table("backtest_runs") as batch:
            batch.drop_constraint(
                "fk_backtest_runs_strategy_id_strategies",
                type_="foreignkey",
            )

    if _has_fk("backtest_runs", "fk_backtest_runs_portfolio_id_portfolios"):
        with op.batch_alter_table("backtest_runs") as batch:
            batch.drop_constraint(
                "fk_backtest_runs_portfolio_id_portfolios",
                type_="foreignkey",
            )

    if _has_unique_constraint("portfolio_snapshots", "uq_snapshot_portfolio_date"):
        with op.batch_alter_table("portfolio_snapshots") as batch:
            batch.drop_constraint(
                "uq_snapshot_portfolio_date",
                type_="unique",
            )

    if _has_fk("portfolio_snapshots", "fk_portfolio_snapshots_portfolio_id_portfolios"):
        with op.batch_alter_table("portfolio_snapshots") as batch:
            batch.drop_constraint(
                "fk_portfolio_snapshots_portfolio_id_portfolios",
                type_="foreignkey",
            )

    if _has_fk("transactions", "fk_transactions_portfolio_id_portfolios"):
        with op.batch_alter_table("transactions") as batch:
            batch.drop_constraint(
                "fk_transactions_portfolio_id_portfolios",
                type_="foreignkey",
            )
