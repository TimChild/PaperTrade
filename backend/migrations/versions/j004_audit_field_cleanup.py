"""audit field cleanup — invocation_mode + deactivation_reason

Phase J follow-up — Issues #278 + #284. Two related audit-row cleanups
bundled into a single revision because they share the same domain and
roughly the same shape (add a dedicated column; stop overloading an
existing one).

Issue #278 — ``TriggerFireRecord.invocation_mode``
==================================================

Adds ``invocation_mode`` to ``trigger_fire_records``. Previously, the
queue-mode path (Pattern B, Phase J / PR #276) persisted
``agent_response = NEEDS_HUMAN`` with a ``{"mode": "queue", ...}``
marker stashed in ``agent_response_raw`` — because the
:class:`AgentDecision` enum couldn't carry a dict. That overloaded the
``NEEDS_HUMAN`` semantics: a real organic human escalation and a
queue-mode fire were indistinguishable on the wire without parsing
``agent_response_raw`` or joining back to the trigger row's ``mode``.

With ``invocation_mode`` as a first-class column:

* Queue-mode fires set ``invocation_mode='queue'`` and may have
  ``agent_response IS NULL`` (no inline agent invocation happened).
* Direct-mode fires set ``invocation_mode='direct'`` and continue to
  populate ``agent_response`` with the structured decision.
* The activity feed + fire-log UI render the "Inline" / "Queued" pill
  from ``invocation_mode`` directly.

Backfill — existing ``trigger_fire_records`` rows:

* Rows whose ``agent_response='NEEDS_HUMAN'`` AND whose
  ``agent_response_raw`` contains ``"mode":"queue"`` are flipped to
  ``invocation_mode='queue'`` and ``agent_response=NULL`` (the original
  queue-mode marker is removed; the resulting_exploration_task_id link
  is what they're for). Clean conversion since ``agent_response_raw``
  is a structured marker.
* All other rows keep ``invocation_mode='direct'`` (the server-side
  default).

``agent_response`` is widened to nullable so queue-mode rows can persist
with no inline decision. The constraint relaxation is forward
compatible — direct-mode rows continue to populate it.

Issue #284 — ``StrategyActivation.deactivation_reason``
=======================================================

Adds ``deactivation_reason`` to ``strategy_activations``. Previously,
``POST /activations/{id}/deactivate`` stored the user-supplied reason
into ``last_error``, which conflated benign user pauses with real
execution failures — alerting / UI keying off "is ``last_error`` set?"
false-positived on every deliberate pause.

With ``deactivation_reason`` as a first-class column:

* The deactivate endpoint writes the reason to ``deactivation_reason``
  and leaves ``last_error`` unchanged.
* ``strategy_execution_service.py`` continues writing actual execution
  failures to ``last_error``.

Backfill: forward-only. Existing rows keep their ``last_error`` value
because we can't reliably distinguish "this is an execution failure"
from "this is a benign pause note someone wrote." A naive heuristic
(no "Error:" / "Traceback") would mis-classify in either direction.
The next deactivate call on each activation will populate
``deactivation_reason`` correctly; until then the row remains as it
was — no regression vs the pre-migration state.

Revision ID: j004_audit_cleanup
Revises: j003_trigger_mode
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. ``j004_audit_cleanup`` is 18
# chars — well under the 32-char cap on ``alembic_version.version_num``.
# Filename can be longer; only the revision id has the cap.
revision: str = "j004_audit_cleanup"
down_revision: str | Sequence[str] | None = "j003_trigger_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FIRES_TABLE: str = "trigger_fire_records"
_ACTIVATIONS_TABLE: str = "strategy_activations"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table_name: str, column_name: str) -> bool:
    if not _inspector().has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    """Add the two columns + apply targeted backfill for trigger fires."""
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # ------------------------------------------------------------------
    # Issue #278 — invocation_mode on trigger_fire_records
    # ------------------------------------------------------------------
    if not _inspector().has_table(_FIRES_TABLE):
        raise RuntimeError(
            f"{_FIRES_TABLE} table is missing — apply earlier migrations "
            "before j004_audit_cleanup."
        )

    if not _has_column(_FIRES_TABLE, "invocation_mode"):
        op.add_column(
            _FIRES_TABLE,
            sa.Column(
                "invocation_mode",
                sa.String(length=16),
                nullable=False,
                server_default="direct",
            ),
        )

    # Widen agent_response to nullable so queue-mode rows can persist
    # without a fabricated NEEDS_HUMAN decision. SQLite needs batch
    # mode to alter column nullability.
    if dialect_name == "sqlite":
        with op.batch_alter_table(_FIRES_TABLE) as batch_op:
            batch_op.alter_column(
                "agent_response",
                existing_type=sa.String(length=30),
                nullable=True,
            )
    else:
        op.alter_column(
            _FIRES_TABLE,
            "agent_response",
            existing_type=sa.String(length=30),
            nullable=True,
        )

    # Backfill — flip queue-mode rows that were written under the old
    # scheme. Detection: agent_response='NEEDS_HUMAN' AND
    # agent_response_raw contains the queue marker. Clear the marker on
    # those rows by zeroing agent_response_raw (the queued task id is
    # already on resulting_exploration_task_id and the row is now
    # discriminated by invocation_mode).
    op.execute(
        sa.text(
            """
            UPDATE trigger_fire_records
            SET invocation_mode = 'queue',
                agent_response = NULL,
                agent_response_raw = ''
            WHERE agent_response = 'NEEDS_HUMAN'
              AND agent_response_raw LIKE '%"mode":"queue"%'
            """
        )
    )

    # ------------------------------------------------------------------
    # Issue #284 — deactivation_reason on strategy_activations
    # ------------------------------------------------------------------
    if not _inspector().has_table(_ACTIVATIONS_TABLE):
        raise RuntimeError(
            f"{_ACTIVATIONS_TABLE} table is missing — apply earlier "
            "migrations before j004_audit_cleanup."
        )

    if not _has_column(_ACTIVATIONS_TABLE, "deactivation_reason"):
        op.add_column(
            _ACTIVATIONS_TABLE,
            sa.Column(
                "deactivation_reason",
                sa.String(length=500),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Drop the two columns; restore agent_response NOT NULL."""
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if _has_column(_ACTIVATIONS_TABLE, "deactivation_reason"):
        op.drop_column(_ACTIVATIONS_TABLE, "deactivation_reason")

    if _has_column(_FIRES_TABLE, "invocation_mode"):
        op.drop_column(_FIRES_TABLE, "invocation_mode")

    # Restoring agent_response NOT NULL would require backfilling the
    # rows we just nulled out. Pick a safe sentinel for the downgrade
    # path (we re-stamp NEEDS_HUMAN on rows we know were queue-mode
    # because resulting_exploration_task_id is set and agent_response
    # IS NULL).
    op.execute(
        sa.text(
            """
            UPDATE trigger_fire_records
            SET agent_response = 'NEEDS_HUMAN'
            WHERE agent_response IS NULL
              AND resulting_exploration_task_id IS NOT NULL
            """
        )
    )

    if dialect_name == "sqlite":
        with op.batch_alter_table(_FIRES_TABLE) as batch_op:
            batch_op.alter_column(
                "agent_response",
                existing_type=sa.String(length=30),
                nullable=False,
            )
    else:
        op.alter_column(
            _FIRES_TABLE,
            "agent_response",
            existing_type=sa.String(length=30),
            nullable=False,
        )
