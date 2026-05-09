"""StrategySnapshot value object - frozen copy of a Strategy at run-time.

Used by ``BacktestRun.strategy_snapshot`` to preserve the strategy
configuration even if the source ``Strategy`` is later edited or deleted.

Wire format note: ``BacktestRun.strategy_snapshot`` is persisted as JSON in
the database. The ``to_dict`` / ``from_dict`` round-trip is the canonical
serialization. ``from_dict`` is intentionally lenient on missing fields to
preserve backward-compatible reads of pre-refactor rows (see audit
`bcode.P0-1`).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import (
    StrategyParameters,
    parameters_from_dict,
)
from zebu.domain.value_objects.strategy_type import StrategyType


@dataclass(frozen=True)
class StrategySnapshot:
    """Immutable snapshot of a Strategy entity captured at backtest run time.

    Mirrors the run-relevant state of a ``Strategy`` (identity, name, type,
    tickers, parameters) so that backtest results stay reproducible even if
    the source strategy is mutated or deleted afterwards.

    Construct via the standard dataclass constructor, passing fields copied
    from the source ``Strategy``. The application layer owns the conversion
    so that this value object stays free of entity imports.

    Attributes:
        strategy_id: ID of the source strategy at the time of capture.
        name: Human-readable strategy name at capture time.
        strategy_type: Algorithm discriminator.
        tickers: Ordered ticker list at capture time.
        parameters: Typed parameters matching ``strategy_type``.
    """

    strategy_id: UUID
    name: str
    strategy_type: StrategyType
    tickers: tuple[str, ...]
    parameters: StrategyParameters

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-friendly dict.

        Returns:
            Dict suitable for storage as a JSON column. Round-trips via
            :meth:`from_dict`.
        """
        return {
            "id": str(self.strategy_id),
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "tickers": list(self.tickers),
            "parameters": self.parameters.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "StrategySnapshot":
        """Reconstruct from a JSON-loaded mapping.

        Lossy-by-design: missing fields raise ``InvalidStrategyError`` only
        when they're load-bearing. This keeps reads of pre-refactor rows
        possible even if individual fields drifted (e.g. an older snapshot
        had ``id`` but no ``parameters``).

        Args:
            raw: Mapping loaded from a JSON column.

        Returns:
            Validated StrategySnapshot.

        Raises:
            InvalidStrategyError: If the mapping cannot be parsed at all
                (unknown ``strategy_type``, missing ``parameters``, etc.).
        """
        type_raw = raw.get("strategy_type")
        if not isinstance(type_raw, str):
            raise InvalidStrategyError("strategy_snapshot is missing 'strategy_type'")
        try:
            strategy_type = StrategyType(type_raw)
        except ValueError as exc:
            raise InvalidStrategyError(
                f"strategy_snapshot has unknown strategy_type {type_raw!r}"
            ) from exc

        params_raw = raw.get("parameters")
        if not isinstance(params_raw, Mapping):
            raise InvalidStrategyError(
                "strategy_snapshot is missing 'parameters' mapping"
            )
        parameters = parameters_from_dict(
            strategy_type, cast("Mapping[str, object]", params_raw)
        )

        id_raw = raw.get("id")
        if not isinstance(id_raw, str):
            raise InvalidStrategyError("strategy_snapshot is missing 'id'")
        try:
            strategy_id = UUID(id_raw)
        except ValueError as exc:
            raise InvalidStrategyError(
                f"strategy_snapshot has invalid 'id' {id_raw!r}"
            ) from exc

        name_raw = raw.get("name")
        name = name_raw if isinstance(name_raw, str) else ""

        tickers_raw = raw.get("tickers")
        tickers: tuple[str, ...]
        if isinstance(tickers_raw, list) and all(
            isinstance(t, str) for t in tickers_raw
        ):
            tickers = tuple(cast("list[str]", tickers_raw))
        else:
            tickers = ()

        return cls(
            strategy_id=strategy_id,
            name=name,
            strategy_type=strategy_type,
            tickers=tickers,
            parameters=parameters,
        )
