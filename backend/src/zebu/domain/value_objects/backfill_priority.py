"""BackfillPriority value object — priority ladder for a backfill task.

Phase J (Task #212 Layer 2) — activation-time pre-warm.

Distinguishes activation-driven prewarms (``LOW``, deferred when the
daily AV cap is exhausted) from operator-triggered backfills (``HIGH``,
pre-empts the daily cap when paid AV is in play). Wire format is the
StrEnum's string value — JSON-friendly and stable across versions.

Lives in the domain layer because the entity ``BackfillTask`` references
it directly; the scheduler and prewarmer both branch on the value.
"""

from enum import StrEnum


class BackfillPriority(StrEnum):
    """Priority of a queued :class:`BackfillTask`.

    Members:
        LOW: Activation-driven prewarm. Defers when the daily Alpha
            Vantage cap is hit (the rate limiter blocks; the next
            scheduler cycle picks the task up again).
        HIGH: Operator- or system-triggered backfill. The Phase J spec
            calls for these to "pre-empt the daily cap" on paid Alpha
            Vantage; the rate-limiter wiring uses ``ALPHA_VANTAGE_DAILY_CAP``
            (``0`` = unbounded) to encode that semantically.
    """

    LOW = "low"
    HIGH = "high"


__all__ = ["BackfillPriority"]
