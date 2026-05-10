"""In-memory implementation of TriggerFireRepository for testing.

Thread-safe. Append-only — duplicate IDs raise ``ValueError`` (mirrors
the SQL adapter's IntegrityError contract).
"""

from threading import Lock
from uuid import UUID

from zebu.domain.entities.trigger_fire_record import TriggerFireRecord


class InMemoryTriggerFireRepository:
    """In-memory implementation of :class:`TriggerFireRepository` protocol."""

    def __init__(self) -> None:
        """Initialise empty fire-record storage."""
        self._records: dict[UUID, TriggerFireRecord] = {}
        self._lock = Lock()

    async def get(self, record_id: UUID) -> TriggerFireRecord | None:
        """Retrieve a fire record by ID."""
        with self._lock:
            return self._records.get(record_id)

    async def list_for_trigger(
        self,
        trigger_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records for one trigger, newest-first."""
        with self._lock:
            matching = [r for r in self._records.values() if r.trigger_id == trigger_id]
            ordered = sorted(matching, key=lambda r: r.fired_at, reverse=True)
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def list_for_activation(
        self,
        activation_id: UUID,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TriggerFireRecord]:
        """List fire records for one activation, newest-first."""
        with self._lock:
            matching = [
                r for r in self._records.values() if r.activation_id == activation_id
            ]
            ordered = sorted(matching, key=lambda r: r.fired_at, reverse=True)
            if limit is None:
                return ordered[offset:]
            return ordered[offset : offset + limit]

    async def count_for_trigger(self, trigger_id: UUID) -> int:
        """Count fire records for one trigger."""
        with self._lock:
            return sum(1 for r in self._records.values() if r.trigger_id == trigger_id)

    async def count_for_activation(self, activation_id: UUID) -> int:
        """Count fire records for one activation."""
        with self._lock:
            return sum(
                1 for r in self._records.values() if r.activation_id == activation_id
            )

    async def save(self, record: TriggerFireRecord) -> None:
        """Insert a fire record. Duplicate ``id`` raises ``ValueError``."""
        with self._lock:
            if record.id in self._records:
                raise ValueError(
                    f"TriggerFireRecord with id={record.id} already exists; "
                    "the audit log is append-only"
                )
            self._records[record.id] = record

    def clear(self) -> None:
        """Clear all records (for testing)."""
        with self._lock:
            self._records.clear()
