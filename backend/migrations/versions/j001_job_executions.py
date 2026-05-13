"""add_job_executions_table

Phase J (Task #212 Layer 1) — job-health observability.

Adds the ``job_executions`` table that stores one audit row per
scheduler-handler invocation. Written by the ``@with_job_audit``
decorator in :mod:`zebu.infrastructure.job_audit`; read by the new
``GET /api/v1/admin/jobs/health`` endpoint.

Schema:

* ``id`` — UUID primary key.
* ``job_name`` — Stable handler identifier (e.g.
  ``"refresh_active_stocks"``). Up to 100 chars.
* ``started_at`` — Naive UTC timestamp when ``record_start`` ran.
* ``finished_at`` — Naive UTC timestamp when ``record_finish`` ran.
  Nullable while the job is in ``RUNNING`` state.
* ``status`` — One of ``RUNNING`` / ``SUCCEEDED`` / ``FAILED``.
* ``error_message`` — Truncated exception message (≤ 500 chars) for
  failed runs.
* ``metadata`` — JSON object payload (free-form ``str -> str``).

Indexes:

* ``idx_job_executions_job_name_started_at`` — backs the per-job
  ``latest`` lookup the health endpoint calls on every request.

The migration is idempotent (uses inspector-based exists checks,
mirroring the pattern in ``f001`` / ``f005``).

Revision ID: j001_job_executions
Revises: f005_trigger_id_on_txns
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. Note: the revision id is 19
# characters — well under the 32-character cap on
# ``alembic_version.version_num``. Filename matches.
revision: str = "j001_job_executions"
down_revision: str | Sequence[str] | None = "f005_trigger_id_on_txns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "job_executions"
_INDEX_JOB_NAME_STARTED_AT: str = "idx_job_executions_job_name_started_at"


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
    """Create the ``job_executions`` table and its compound index."""
    if not _has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("job_name", sa.String(length=100), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index(_TABLE, _INDEX_JOB_NAME_STARTED_AT):
        op.create_index(
            _INDEX_JOB_NAME_STARTED_AT,
            _TABLE,
            ["job_name", "started_at"],
        )


def downgrade() -> None:
    """Drop the index then the table."""
    if _has_index(_TABLE, _INDEX_JOB_NAME_STARTED_AT):
        op.drop_index(_INDEX_JOB_NAME_STARTED_AT, table_name=_TABLE)
    if _has_table(_TABLE):
        op.drop_table(_TABLE)
