"""ConditionType + ConditionParams value objects — discriminated trigger conditions.

A :class:`StrategyConditionTrigger` carries a ``condition_type`` enum
value and a typed ``condition_params`` value object (one frozen dataclass
per condition type). The pattern matches
``zebu.domain.value_objects.strategy_parameters`` exactly:

* ``ConditionType`` is the discriminator — a :class:`StrEnum` so the value
  round-trips through JSON cleanly (matches ``ActivationStatus``,
  ``BacktestStatus``, etc.).
* ``ConditionParams`` is a discriminated-union ``type`` alias of the
  per-type frozen dataclasses.
* :func:`params_from_dict` reconstructs the typed VO from the JSON column
  on the trigger row, mirroring :func:`parameters_from_dict` for strategy
  parameters.

Per Phase-F §1.2 / Q1: frozen dataclasses (not Pydantic) for parity with
the existing strategy-parameters pattern. Construction-time validation
raises :class:`InvalidTriggerError`.

``CUSTOM_RULE`` is intentionally **not implemented** — :func:`params_from_dict`
on a ``CUSTOM_RULE`` discriminator raises with a clear "not yet supported"
message. The enum value exists so the wire-format (and the API spec in
F-2 / F-5) is forward-compatible without committing to an evaluation
implementation. See Phase F design Q1 + Q2.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from zebu.domain.exceptions import InvalidTriggerError
from zebu.domain.value_objects.ticker import Ticker

# Schema-version constant carried on serialised condition params + on
# ``TriggerFireRecord.condition_evaluation_data`` (per Phase-F design Q8).
# Cheap forward-compat tagging — bump if the on-wire shape changes.
CONDITION_PARAMS_SCHEMA_VERSION: int = 1


class ConditionType(StrEnum):
    """Discriminator for which kind of condition a trigger evaluates.

    Values:
        DRAWDOWN_THRESHOLD: Fires when portfolio (or any single ticker) is
            down >= ``threshold_pct`` from its lookback-window peak.
        VOLATILITY_SPIKE: Fires when realised volatility over
            ``over_days`` exceeds ``threshold_pct`` (annualised).
        EARNINGS_PROXIMITY: Fires when any covered ticker's next earnings
            date is within ``days_before`` trading days of now.
        CUSTOM_RULE: Reserved scaffold; constructing a trigger with this
            type currently raises ``InvalidTriggerError``. Implementation
            deferred to a follow-up because safe predicate evaluation is
            its own design problem (Phase F design Q1).
    """

    DRAWDOWN_THRESHOLD = "DRAWDOWN_THRESHOLD"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    EARNINGS_PROXIMITY = "EARNINGS_PROXIMITY"
    CUSTOM_RULE = "CUSTOM_RULE"


class DrawdownMetric(StrEnum):
    """Which drawdown view to compute for a ``DRAWDOWN_THRESHOLD`` trigger.

    Values:
        PORTFOLIO_TOTAL: Fires on portfolio-level drawdown (default).
        PER_TICKER: Fires when any single ticker's drawdown crosses the
            threshold — useful for "tell me if any single name in this
            basket cracks 5% from peak".
    """

    PORTFOLIO_TOTAL = "PORTFOLIO_TOTAL"
    PER_TICKER = "PER_TICKER"


def _coerce_decimal(value: object, field_name: str) -> Decimal:
    """Coerce a JSON-friendly value (Decimal / str / int / float) to Decimal.

    Args:
        value: Raw value (typically loaded from JSON).
        field_name: Field name used in error messages.

    Returns:
        Decimal-coerced value.

    Raises:
        InvalidTriggerError: If the value cannot be coerced to a finite
            Decimal.
    """
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidTriggerError(f"'{field_name}' must be a finite number")
        return value
    if isinstance(value, bool):
        # bool is a subclass of int — reject it explicitly.
        raise InvalidTriggerError(f"'{field_name}' must be a number, got bool")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise InvalidTriggerError(
                f"'{field_name}' is not a valid number: {value!r}"
            ) from exc
        if not result.is_finite():
            raise InvalidTriggerError(f"'{field_name}' must be a finite number")
        return result
    if isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise InvalidTriggerError(
                f"'{field_name}' is not a valid number: {value!r}"
            ) from exc
        if not result.is_finite():
            raise InvalidTriggerError(f"'{field_name}' must be a finite number")
        return result
    raise InvalidTriggerError(
        f"'{field_name}' must be a number, got {type(value).__name__}"
    )


def _coerce_int(value: object, field_name: str) -> int:
    """Coerce a JSON-friendly value to int (no float / bool acceptance).

    Args:
        value: Raw value.
        field_name: Field name used in error messages.

    Returns:
        int value.

    Raises:
        InvalidTriggerError: If the value is not a non-bool int.
    """
    if isinstance(value, bool):
        raise InvalidTriggerError(f"'{field_name}' must be an integer, got bool")
    if isinstance(value, int):
        return value
    raise InvalidTriggerError(
        f"'{field_name}' must be an integer, got {type(value).__name__}"
    )


def _coerce_tickers(value: object, field_name: str) -> list[Ticker]:
    """Coerce a JSON-friendly value (list of strings) to ``list[Ticker]``.

    Each entry is run through the :class:`Ticker` constructor so the
    domain validation (1-5 uppercase letters) is enforced. Empty lists
    raise — callers wanting "all tickers" should pass ``None``, not
    ``[]``, to avoid an ambiguous wire-format.

    Args:
        value: Raw value (typically a JSON list of strings).
        field_name: Field name used in error messages.

    Returns:
        List of validated :class:`Ticker` instances.

    Raises:
        InvalidTriggerError: If the value is not a list, contains
            non-strings, or is empty.
    """
    if not isinstance(value, list):
        raise InvalidTriggerError(
            f"'{field_name}' must be a non-empty list of ticker strings, "
            f"got {type(value).__name__}"
        )
    if len(value) == 0:
        raise InvalidTriggerError(
            f"'{field_name}' must be a non-empty list when set; "
            "use None to mean 'all tickers'"
        )
    tickers: list[Ticker] = []
    for entry in value:
        if not isinstance(entry, str):
            raise InvalidTriggerError(
                f"'{field_name}' entries must be ticker strings, "
                f"got {type(entry).__name__}"
            )
        # Ticker() raises InvalidTickerError on bad shape; let it propagate.
        tickers.append(Ticker(entry))
    return tickers


@dataclass(frozen=True)
class DrawdownParams:
    """Parameters for a ``DRAWDOWN_THRESHOLD`` trigger.

    Fires when the activation's portfolio (or any single ticker, depending
    on ``metric``) is down ``>= threshold_pct`` from its
    ``lookback_days``-window peak.

    Attributes:
        threshold_pct: Drawdown percentage that fires the trigger. Must be
            ``> 0`` and ``<= 100``. Stored as Decimal for exact comparison.
        lookback_days: Window over which drawdown is measured. Must be in
            ``[1, 365]``.
        metric: Which drawdown view to compute. Defaults to
            :class:`DrawdownMetric.PORTFOLIO_TOTAL`.

    Raises:
        InvalidTriggerError: If any field is out of range.
    """

    threshold_pct: Decimal
    lookback_days: int
    metric: DrawdownMetric = DrawdownMetric.PORTFOLIO_TOTAL

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.threshold_pct.is_finite():
            raise InvalidTriggerError(
                "DrawdownParams.threshold_pct must be a finite number"
            )
        if self.threshold_pct <= Decimal("0") or self.threshold_pct > Decimal("100"):
            raise InvalidTriggerError(
                f"DrawdownParams.threshold_pct must be in (0, 100], "
                f"got {self.threshold_pct}"
            )
        if isinstance(self.lookback_days, bool):
            raise InvalidTriggerError(
                "DrawdownParams.lookback_days must be an integer in [1, 365]"
            )
        if not (1 <= self.lookback_days <= 365):
            raise InvalidTriggerError(
                f"DrawdownParams.lookback_days must be in [1, 365], "
                f"got {self.lookback_days}"
            )

    def to_dict(self) -> dict[str, object]:
        """Serialise to a JSON-friendly mapping."""
        return {
            "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
            "threshold_pct": str(self.threshold_pct),
            "lookback_days": self.lookback_days,
            "metric": self.metric.value,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "DrawdownParams":
        """Reconstruct from a JSON-loaded mapping.

        Raises:
            InvalidTriggerError: If required fields are missing or invalid.
        """
        threshold_raw = raw.get("threshold_pct")
        if threshold_raw is None:
            raise InvalidTriggerError("DrawdownParams requires a 'threshold_pct' field")
        lookback_raw = raw.get("lookback_days")
        if lookback_raw is None:
            raise InvalidTriggerError("DrawdownParams requires a 'lookback_days' field")
        metric_raw = raw.get("metric", DrawdownMetric.PORTFOLIO_TOTAL.value)
        if not isinstance(metric_raw, str):
            raise InvalidTriggerError(
                f"DrawdownParams.metric must be a string, "
                f"got {type(metric_raw).__name__}"
            )
        try:
            metric = DrawdownMetric(metric_raw)
        except ValueError as exc:
            raise InvalidTriggerError(
                f"DrawdownParams.metric must be one of "
                f"{[m.value for m in DrawdownMetric]}, got {metric_raw!r}"
            ) from exc
        return cls(
            threshold_pct=_coerce_decimal(threshold_raw, "threshold_pct"),
            lookback_days=_coerce_int(lookback_raw, "lookback_days"),
            metric=metric,
        )


@dataclass(frozen=True)
class VolatilityParams:
    """Parameters for a ``VOLATILITY_SPIKE`` trigger.

    Fires when the realised volatility (annualised) of any covered ticker
    over ``over_days`` exceeds ``threshold_pct``.

    Attributes:
        threshold_pct: Annualised realised-volatility threshold.
            Must be ``> 0`` and ``<= 100``.
        over_days: Window for realised-volatility computation. Must be in
            ``[5, 90]``.
        tickers: When ``None``, applies to all of the strategy's tickers;
            when set, restricts evaluation to the given subset. The
            subset-of-strategy-tickers check is enforced at the API layer
            (it needs the strategy entity), not here — this VO only
            validates the list shape (non-empty, valid ticker strings).

    Raises:
        InvalidTriggerError: If any field is out of range.
    """

    threshold_pct: Decimal
    over_days: int
    tickers: list[Ticker] | None = None

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not self.threshold_pct.is_finite():
            raise InvalidTriggerError(
                "VolatilityParams.threshold_pct must be a finite number"
            )
        if self.threshold_pct <= Decimal("0") or self.threshold_pct > Decimal("100"):
            raise InvalidTriggerError(
                f"VolatilityParams.threshold_pct must be in (0, 100], "
                f"got {self.threshold_pct}"
            )
        if isinstance(self.over_days, bool):
            raise InvalidTriggerError(
                "VolatilityParams.over_days must be an integer in [5, 90]"
            )
        if not (5 <= self.over_days <= 90):
            raise InvalidTriggerError(
                f"VolatilityParams.over_days must be in [5, 90], got {self.over_days}"
            )
        if self.tickers is not None and len(self.tickers) == 0:
            raise InvalidTriggerError(
                "VolatilityParams.tickers must be None or a non-empty list; "
                "use None to mean 'all strategy tickers'"
            )

    def to_dict(self) -> dict[str, object]:
        """Serialise to a JSON-friendly mapping."""
        return {
            "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
            "threshold_pct": str(self.threshold_pct),
            "over_days": self.over_days,
            "tickers": (
                [t.symbol for t in self.tickers] if self.tickers is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "VolatilityParams":
        """Reconstruct from a JSON-loaded mapping.

        Raises:
            InvalidTriggerError: If required fields are missing or invalid.
        """
        threshold_raw = raw.get("threshold_pct")
        if threshold_raw is None:
            raise InvalidTriggerError(
                "VolatilityParams requires a 'threshold_pct' field"
            )
        over_raw = raw.get("over_days")
        if over_raw is None:
            raise InvalidTriggerError("VolatilityParams requires an 'over_days' field")
        tickers_raw = raw.get("tickers")
        tickers: list[Ticker] | None
        if tickers_raw is None:
            tickers = None
        else:
            tickers = _coerce_tickers(tickers_raw, "tickers")
        return cls(
            threshold_pct=_coerce_decimal(threshold_raw, "threshold_pct"),
            over_days=_coerce_int(over_raw, "over_days"),
            tickers=tickers,
        )


@dataclass(frozen=True)
class EarningsParams:
    """Parameters for an ``EARNINGS_PROXIMITY`` trigger.

    Fires when any covered ticker's next scheduled earnings date is within
    ``days_before`` trading days of now. The earnings calendar source is
    abstracted behind ``EarningsCalendarPort`` (lands in F-4); F-1 only
    encodes the parameters.

    Attributes:
        days_before: Trigger fires when next earnings is within this many
            trading days. Must be in ``[1, 14]``.
        tickers: Same semantics as :class:`VolatilityParams.tickers` —
            ``None`` means "all of the strategy's tickers"; a non-empty
            list restricts the subset.

    Raises:
        InvalidTriggerError: If any field is out of range.
    """

    days_before: int
    tickers: list[Ticker] | None = None

    def __post_init__(self) -> None:
        """Validate parameters."""
        if isinstance(self.days_before, bool):
            raise InvalidTriggerError(
                "EarningsParams.days_before must be an integer in [1, 14]"
            )
        if not (1 <= self.days_before <= 14):
            raise InvalidTriggerError(
                f"EarningsParams.days_before must be in [1, 14], got {self.days_before}"
            )
        if self.tickers is not None and len(self.tickers) == 0:
            raise InvalidTriggerError(
                "EarningsParams.tickers must be None or a non-empty list; "
                "use None to mean 'all strategy tickers'"
            )

    def to_dict(self) -> dict[str, object]:
        """Serialise to a JSON-friendly mapping."""
        return {
            "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
            "days_before": self.days_before,
            "tickers": (
                [t.symbol for t in self.tickers] if self.tickers is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "EarningsParams":
        """Reconstruct from a JSON-loaded mapping.

        Raises:
            InvalidTriggerError: If required fields are missing or invalid.
        """
        days_raw = raw.get("days_before")
        if days_raw is None:
            raise InvalidTriggerError("EarningsParams requires a 'days_before' field")
        tickers_raw = raw.get("tickers")
        tickers: list[Ticker] | None
        if tickers_raw is None:
            tickers = None
        else:
            tickers = _coerce_tickers(tickers_raw, "tickers")
        return cls(
            days_before=_coerce_int(days_raw, "days_before"),
            tickers=tickers,
        )


@dataclass(frozen=True)
class CustomRuleParams:
    """Reserved scaffold for ``CUSTOM_RULE`` — not yet implemented.

    The :func:`params_from_dict` factory and the entity constructor
    intentionally reject any attempt to build a trigger with
    :class:`ConditionType.CUSTOM_RULE` so the wire format stays
    forward-compatible without committing to an evaluation strategy. See
    Phase F design Q1.

    Constructing this dataclass directly always raises
    :class:`InvalidTriggerError`. The dataclass exists so the discriminated
    union ``ConditionParams`` includes a placeholder type for completeness.
    """

    # The raw payload is held for future round-tripping; we keep it
    # opaque so callers don't accidentally depend on a shape that hasn't
    # been designed yet. ``field(default_factory=dict)`` keeps the
    # dataclass frozen-friendly.
    raw: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject construction — CUSTOM_RULE is intentionally unimplemented."""
        raise InvalidTriggerError(
            "CUSTOM_RULE triggers are not yet supported. "
            "See Phase F design doc Q1 — predicate evaluation is its own "
            "design problem and is deferred to a follow-up issue."
        )

    def to_dict(self) -> dict[str, object]:
        """Serialise — never reached because construction always raises."""
        return {
            "schema_version": CONDITION_PARAMS_SCHEMA_VERSION,
            "raw": dict(self.raw),
        }

    @classmethod
    def from_dict(
        cls, raw: Mapping[str, object]
    ) -> "CustomRuleParams":  # pragma: no cover
        """Factory — always raises via ``__post_init__``."""
        return cls(raw=raw)


# Discriminated-union type alias. The discriminator is
# :class:`ConditionType` — downstream code matches via ``isinstance`` /
# ``match`` on the concrete subtype.
type ConditionParams = (
    DrawdownParams | VolatilityParams | EarningsParams | CustomRuleParams
)


_PARAMS_BY_TYPE: dict[
    ConditionType,
    type[DrawdownParams]
    | type[VolatilityParams]
    | type[EarningsParams]
    | type[CustomRuleParams],
] = {
    ConditionType.DRAWDOWN_THRESHOLD: DrawdownParams,
    ConditionType.VOLATILITY_SPIKE: VolatilityParams,
    ConditionType.EARNINGS_PROXIMITY: EarningsParams,
    ConditionType.CUSTOM_RULE: CustomRuleParams,
}


def params_from_dict(
    condition_type: ConditionType, raw: Mapping[str, object]
) -> ConditionParams:
    """Reconstruct typed :class:`ConditionParams` from the JSON column.

    Args:
        condition_type: The trigger's :class:`ConditionType` discriminator.
        raw: JSON-loaded parameter mapping (e.g. from the trigger row's
            ``condition_params`` column or an API request body).

    Returns:
        Validated :class:`ConditionParams` instance of the appropriate
        concrete subtype.

    Raises:
        InvalidTriggerError: If the mapping is missing required fields,
            contains invalid values, or the discriminator is
            ``CUSTOM_RULE`` (which is unimplemented per Phase F design Q1).
    """
    params_cls = _PARAMS_BY_TYPE.get(condition_type)
    if params_cls is None:
        raise InvalidTriggerError(
            f"Unsupported ConditionType discriminator: {condition_type.value}"
        )
    if condition_type is ConditionType.CUSTOM_RULE:
        # Surface the same "not yet supported" message the dataclass
        # would raise on direct construction. Keeps the message
        # consistent for both call paths.
        raise InvalidTriggerError(
            "CUSTOM_RULE triggers are not yet supported. "
            "See Phase F design doc Q1 — predicate evaluation is its own "
            "design problem and is deferred to a follow-up issue."
        )
    return params_cls.from_dict(raw)


def params_match_type(condition_type: ConditionType, params: ConditionParams) -> bool:
    """Check whether ``params`` is the concrete dataclass for ``condition_type``.

    Used by the entity's ``__post_init__`` invariant to reject mismatches
    like ``ConditionType.DRAWDOWN_THRESHOLD`` paired with a
    :class:`VolatilityParams`.

    Args:
        condition_type: Discriminator.
        params: Typed parameter instance.

    Returns:
        ``True`` if ``params`` is the expected concrete dataclass for the
        discriminator.
    """
    expected = _PARAMS_BY_TYPE.get(condition_type)
    return expected is not None and isinstance(params, expected)
