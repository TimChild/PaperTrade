"""add_backtest_agent_invocations_and_run_invocation_mode

Phase L-1 (Task #217) — Foundation for the agent-driven backtest pipeline.

Adds:

* ``backtest_agent_invocations`` table — append-only audit row, one per
  simulated trigger fire inside a backtest. Mirrors
  ``trigger_fire_records`` in spirit but with a ``simulated_date`` column
  (the in-simulation calendar day) and a ``backtest_run_id`` FK that
  cascade-deletes with the parent run.

* ``backtest_runs.agent_invocation_mode`` column — VARCHAR(16) NOT NULL
  DEFAULT 'none'. Records the operator's per-run choice
  (``none`` / ``mock`` / ``live``) on the run row itself so the UI /
  activity feed can label a run without scanning the audit table, and
  to disambiguate "zero audit rows = NONE-mode" from "zero rows = LIVE
  with no fires".

Indexes:

* ``idx_bt_agent_invocation_run_date`` — ``(backtest_run_id, simulated_date)``.
  Backs ``list_for_backtest_run`` chronological ordering and the per-run
  count.
* ``idx_bt_agent_invocation_trigger`` — ``(trigger_id)``. Backs
  retrospective "all backtest invocations of a given trigger" analytics
  queries (not in scope for L-1 but cheap to add now to avoid a follow-
  up migration).

Foreign-key behaviour:

* ``backtest_run_id`` -> ``backtest_runs.id`` ON DELETE CASCADE — deleting
  a backtest run removes all its audit rows.
* ``trigger_id`` -> ``strategy_condition_triggers.id`` ON DELETE SET NULL
  — deleting a trigger orphans rows; audit preserved.
* ``simulated_trade_id`` -> ``transactions.id`` ON DELETE SET NULL —
  deleting an orphan transaction shouldn't lose the rationale.

The migration is idempotent (uses inspector-based exists checks for the
table, the column on ``backtest_runs``, and the two indexes).

Revision ID: l001_backtest_agent_invocations
Revises: j004_audit_cleanup
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. The id is 31 characters — under
# the 32-char cap on ``alembic_version.version_num``. Filename matches.
revision: str = "l001_backtest_agent_invocations"
down_revision: str | Sequence[str] | None = "j004_audit_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "backtest_agent_invocations"
_RUN_TABLE: str = "backtest_runs"
_RUN_COLUMN: str = "agent_invocation_mode"
_INDEX_RUN_DATE: str = "idx_bt_agent_invocation_run_date"
_INDEX_TRIGGER: str = "idx_bt_agent_invocation_trigger"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    """Create the new audit table and add the run-level mode column."""
    # Sanity-check FK target tables exist before declaring constraints.
    for required in (
        "backtest_runs",
        "strategy_condition_triggers",
        "transactions",
    ):
        if not _has_table(required):
            raise RuntimeError(
                f"{required} table is missing — apply earlier migrations "
                "before l001_backtest_agent_invocations."
            )

    # ------------------------------------------------------------------
    # backtest_agent_invocations (append-only audit)
    # ------------------------------------------------------------------
    if not _has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("backtest_run_id", sa.Uuid(), nullable=False),
            sa.Column("simulated_date", sa.Date(), nullable=False),
            sa.Column("trigger_id", sa.Uuid(), nullable=True),
            sa.Column("condition_evaluation_data", sa.JSON(), nullable=False),
            sa.Column("agent_decision", sa.String(length=30), nullable=True),
            sa.Column("rationale", sa.String(length=8000), nullable=False),
            sa.Column("decision_payload", sa.JSON(), nullable=True),
            sa.Column(
                "decision_executed",
                sa.Boolean(),
                nullable=False,
                # ``sa.false()`` so the default renders as a typed
                # boolean literal on Postgres (``FALSE``) rather than
                # ``0`` — asyncpg rejects ``0`` against a BOOLEAN column.
                # SQLite accepts both representations transparently.
                server_default=sa.false(),
            ),
            sa.Column("simulated_trade_id", sa.Uuid(), nullable=True),
            sa.Column("invocation_mode", sa.String(length=16), nullable=False),
            sa.Column("agent_invocation_id", sa.String(length=200), nullable=True),
            sa.Column(
                "latency_ms",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "model",
                sa.String(length=100),
                nullable=False,
                server_default="",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["backtest_run_id"],
                ["backtest_runs.id"],
                name="fk_bt_agent_invocation_run",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["trigger_id"],
                ["strategy_condition_triggers.id"],
                name="fk_bt_agent_invocation_trigger",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["simulated_trade_id"],
                ["transactions.id"],
                name="fk_bt_agent_invocation_simulated_trade",
                ondelete="SET NULL",
            ),
        )

    if not _has_index(_TABLE, _INDEX_RUN_DATE):
        op.create_index(
            _INDEX_RUN_DATE,
            _TABLE,
            ["backtest_run_id", "simulated_date"],
        )

    if not _has_index(_TABLE, _INDEX_TRIGGER):
        op.create_index(
            _INDEX_TRIGGER,
            _TABLE,
            ["trigger_id"],
        )

    # ------------------------------------------------------------------
    # backtest_runs.agent_invocation_mode (per-run durable mode)
    # ------------------------------------------------------------------
    if not _has_column(_RUN_TABLE, _RUN_COLUMN):
        op.add_column(
            _RUN_TABLE,
            sa.Column(
                _RUN_COLUMN,
                sa.String(length=16),
                nullable=False,
                server_default="none",
            ),
        )


def downgrade() -> None:
    """Drop the audit table and the run-level mode column."""
    # Drop the run-table column first so the column-existence check is
    # cheap even if the audit-table drop runs in a partial state.
    if _has_column(_RUN_TABLE, _RUN_COLUMN):
        op.drop_column(_RUN_TABLE, _RUN_COLUMN)

    if _has_index(_TABLE, _INDEX_TRIGGER):
        op.drop_index(_INDEX_TRIGGER, table_name=_TABLE)
    if _has_index(_TABLE, _INDEX_RUN_DATE):
        op.drop_index(_INDEX_RUN_DATE, table_name=_TABLE)
    if _has_table(_TABLE):
        op.drop_table(_TABLE)
