"""ActivationFrequency value object - cadence at which a strategy executes."""

from enum import Enum


class ActivationFrequency(Enum):
    """Represents how often an active strategy is executed by the scheduler.

    Phase C1 ships with a single cadence (``DAILY_MARKET_CLOSE``) — the
    enum exists so adding intraday or weekly frequencies later is a
    schema-compatible change rather than a refactor.

    Members:
        DAILY_MARKET_CLOSE: Run once per trading day, after the daily market
            data refresh (the only cadence supported in Phase C1.1).
    """

    DAILY_MARKET_CLOSE = "DAILY_MARKET_CLOSE"
