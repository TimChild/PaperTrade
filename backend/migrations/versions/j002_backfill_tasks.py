"""add_backfill_tasks_table

Phase J (Task #212 Layer 2) — activation-time pre-warm.

Adds the ``backfill_tasks`` table that stores one row per queued
historical-data fetch. Rows are written by the
:class:`HistoricalDataPrewarmer` (post-activation) and the operator-driven
backfill endpoint (Layer 4); they walk PENDING -> RUNNING -> SUCCEEDED /
FAILED as the scheduler's pickup loop drains them.

Schema:

* ``id`` — UUID primary key.
* ``ticker`` — Stock symbol (up to 10 chars; generous against the
  current 1–5 char Ticker VO).
* ``start_date`` / ``end_date`` — Requested range, both inclusive.
* ``priority`` — ``low`` or ``high`` (see :class:`BackfillPriority`).
* ``status`` — ``pending`` / ``running`` / ``succeeded`` / ``failed``.
* ``created_at`` — Naive UTC timestamp when the task was enqueued.
* ``finished_at`` — Naive UTC timestamp when the task reached a
  terminal status. Nullable while PENDING / RUNNING.
* ``error_message`` — Truncated reason (≤ 500 chars) for FAILED rows.

Indexes:

* ``idx_backfill_tasks_status_created_at`` — backs the scheduler's
  pickup-loop scan (``WHERE status = 'pending' ORDER BY created_at``).

The migration is idempotent (uses inspector-based exists checks,
mirroring the j001 / f001 / f005 pattern).

Revision ID: j002_backfill_tasks
Revises: j001_job_executions
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. ``j002_backfill_tasks`` is 19
# chars — well under the 32-char cap on ``alembic_version.version_num``.
# Filename matches.
revision: str = "j002_backfill_tasks"
down_revision: str | Sequence[str] | None = "j001_job_executions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "backfill_tasks"
_INDEX_STATUS_CREATED_AT: str = "idx_backfill_tasks_status_created_at"


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
    """Create the ``backfill_tasks`` table and its compound index."""
    if not _has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("priority", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index(_TABLE, _INDEX_STATUS_CREATED_AT):
        op.create_index(
            _INDEX_STATUS_CREATED_AT,
            _TABLE,
            ["status", "created_at"],
        )


def downgrade() -> None:
    """Drop the index then the table."""
    if _has_index(_TABLE, _INDEX_STATUS_CREATED_AT):
        op.drop_index(_INDEX_STATUS_CREATED_AT, table_name=_TABLE)
    if _has_table(_TABLE):
        op.drop_table(_TABLE)
