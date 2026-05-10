"""add_trigger_id_to_transactions

Phase F-5 — adds a nullable ``trigger_id`` column (FK ->
``strategy_condition_triggers.id``, ``ON DELETE SET NULL``) to the
``transactions`` table. The activity feed (Phase H2) and the new
trigger fire log API (this PR) join on this column to connect a trade
back to the trigger fire that produced it.

Why ``ON DELETE SET NULL`` rather than CASCADE: the trigger's lifecycle
is independent of the trades it caused; deleting (or hard-removing) a
trigger should not erase historical trade records. Detaching the
credential reference matches the same posture used by ``api_key_id``
in the H2 audit migration.

Indexes:

* ``idx_transaction_trigger_id`` covers the simple ``WHERE trigger_id =
  ?`` lookup used when activity-feed rendering joins back from a fire
  record's ``resulting_trade_id`` to find the canonical transaction.
* ``idx_transaction_trigger_created_at`` (composite ``trigger_id,
  created_at``) backs the per-trigger fire-log read pattern: "all
  trades by this trigger, newest-first" without a sort step in the
  query plan.

Revision ID: f005_trigger_id_on_txns
Revises: f001_trigger_entities
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. Note: the revision id is 26
# characters — well under the 32-character cap on
# ``alembic_version.version_num``. Filename matches.
revision: str = "f005_trigger_id_on_txns"
down_revision: str | Sequence[str] | None = "f001_trigger_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "transactions"
_COLUMN: str = "trigger_id"
_FK_NAME: str = "fk_transactions_trigger_id_strategy_condition_triggers"
_INDEX_SIMPLE: str = "idx_transaction_trigger_id"
_INDEX_COMPOSITE: str = "idx_transaction_trigger_created_at"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _has_fk(table_name: str, fk_name: str) -> bool:
    if not _has_table(table_name):
        return False
    fks = _inspector().get_foreign_keys(table_name)
    return any(fk.get("name") == fk_name for fk in fks)


def upgrade() -> None:
    """Add nullable ``trigger_id`` + FK + indexes to ``transactions``.

    Uses ``batch_alter_table`` so SQLite (which cannot ALTER an existing
    table to add a foreign key) gets a transparent CREATE+COPY+DROP
    rebuild while Postgres gets a normal ALTER.
    """
    if not _has_table("strategy_condition_triggers"):
        # The strategy_condition_triggers table is the FK target; if it's
        # not present the f001 migration hasn't run. Bail with a clear
        # message rather than letting the FK creation fail mid-batch.
        raise RuntimeError(
            "strategy_condition_triggers table is missing — apply migration "
            "f001_trigger_entities before f005_trigger_id_on_txns."
        )

    if not _has_table(_TABLE):
        # Defensive: an early-stage clone that hasn't created the
        # transactions table at all skips the migration cleanly.
        return

    if not _has_column(_TABLE, _COLUMN):
        with op.batch_alter_table(_TABLE) as batch:
            batch.add_column(
                sa.Column(_COLUMN, sa.Uuid(), nullable=True),
            )

    if not _has_fk(_TABLE, _FK_NAME):
        with op.batch_alter_table(_TABLE) as batch:
            batch.create_foreign_key(
                _FK_NAME,
                "strategy_condition_triggers",
                [_COLUMN],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_index(_TABLE, _INDEX_SIMPLE):
        op.create_index(
            _INDEX_SIMPLE,
            _TABLE,
            [_COLUMN],
        )

    if not _has_index(_TABLE, _INDEX_COMPOSITE):
        op.create_index(
            _INDEX_COMPOSITE,
            _TABLE,
            [_COLUMN, "created_at"],
        )


def downgrade() -> None:
    """Drop the indexes, FK, and column in reverse order.

    SQLite handles the column + FK drops via ``batch_alter_table``'s
    rebuild path. Indexes must come off before the column they cover.
    """
    if _has_index(_TABLE, _INDEX_COMPOSITE):
        op.drop_index(_INDEX_COMPOSITE, table_name=_TABLE)

    if _has_index(_TABLE, _INDEX_SIMPLE):
        op.drop_index(_INDEX_SIMPLE, table_name=_TABLE)

    if _has_fk(_TABLE, _FK_NAME):
        with op.batch_alter_table(_TABLE) as batch:
            batch.drop_constraint(_FK_NAME, type_="foreignkey")

    if _has_column(_TABLE, _COLUMN):
        with op.batch_alter_table(_TABLE) as batch:
            batch.drop_column(_COLUMN)
