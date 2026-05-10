"""TriggerFireRepository port — persistence contract for the audit log.

Append-only repository for :class:`TriggerFireRecord`. There are no
update or delete paths exposed — the table is the canonical "what
happened" log; corrections are made by appending new rows or via direct
SQL in pathological cases (audit-trail integrity over flexibility).

Implementations live in:

* ``adapters/outbound/database/trigger_fire_repository.py`` — SQLModel
  backed by Postgres / SQLite.
* ``application/ports/in_memory_trigger_fire_repository.py`` — in-memory
  adapter used by unit / integration tests.

Newest-first ordering on the list methods matches how the activity feed
renders the data (Phase G).
"""

from typing import Protocol
from uuid import UUID

from zebu.domain.entities.trigger_fire_record import TriggerFireRecord


class TriggerFireRepository(Protocol):
    """Persistence contract for :class:`TriggerFireRecord` entities.

    Append-only. Insert (``save``) and read (``get``, ``list_*``,
    ``count_*``) methods are exposed; no update / delete.
    """

    async def get(self, record_id: UUID) -> TriggerFireRecord | None:
        """Retrieve a single fire record by ID.

        Args:
            record_id: Unique record identifier.

        Returns:
            The :class:`TriggerFireRecord` if found, ``None`` otherwise.
        """
        ...

    async def list_for_trigger(
        self,
        trigger_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records for one trigger, newest-first.

        Args:
            trigger_id: Trigger whose fires to fetch.
            limit: Optional row cap. ``None`` means no cap.
            offset: Number of rows to skip for pagination.

        Returns:
            List of records ordered by ``fired_at`` descending.
        """
        ...

    async def list_for_activation(
        self,
        activation_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records across all triggers on one activation.

        The denormalised ``activation_id`` column on the row makes this
        fast — no join required. Used by the per-activation activity
        panel (Phase G).

        Args:
            activation_id: Activation whose fire log to fetch.
            limit: Optional row cap. ``None`` means no cap.
            offset: Number of rows to skip for pagination.

        Returns:
            List of records ordered by ``fired_at`` descending.
        """
        ...

    async def count_for_trigger(self, trigger_id: UUID) -> int:
        """Total fires for one trigger (used by paginated list endpoints).

        Args:
            trigger_id: Trigger whose fire count to compute.

        Returns:
            Count of fire records for the trigger.
        """
        ...

    async def count_for_activation(self, activation_id: UUID) -> int:
        """Total fires for one activation (used by paginated list endpoints).

        Args:
            activation_id: Activation whose fire count to compute.

        Returns:
            Count of fire records for the activation.
        """
        ...

    async def save(self, record: TriggerFireRecord) -> None:
        """Insert a fire record. Duplicate ``id`` raises.

        Implementations MUST treat this as insert-only — the record is
        immutable, and a duplicate ID indicates a programming error
        (e.g. retrying the same write).

        Args:
            record: Entity to persist.

        Raises:
            ValueError: If a record with the same ``id`` already exists.
                Mapped to whichever exception the underlying engine
                raises (e.g. ``IntegrityError`` for SQL implementations);
                the in-memory implementation raises this directly.
        """
        ...
