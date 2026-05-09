"""StrategyParameters value objects - per-strategy-type typed parameter dataclasses.

Replaces ``Strategy.parameters: dict[str, Any]`` with a discriminated union of
frozen dataclasses, one per ``StrategyType``. Each dataclass enforces
strategy-specific invariants at construction (e.g. allocation fractions sum
to ~1.0, fast_window < slow_window) and provides JSON round-trip via
``to_dict`` / ``from_dict``.

Discriminator: the API/database JSON shape carries no explicit "type" field
on the parameters themselves — the discriminator is ``Strategy.strategy_type``.
This keeps the wire format backward compatible with the existing frontend.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_type import StrategyType

# Tolerance for allocation fraction sums — fractions must sum to within this
# distance of 1.0. Mirrors the API-layer tolerance prior to refactor.
_ALLOCATION_SUM_TOLERANCE = Decimal("0.001")


def _coerce_decimal(value: object, field_name: str) -> Decimal:
    """Coerce a JSON-friendly value (Decimal, str, int, float) to Decimal.

    Args:
        value: Raw value (typically loaded from JSON)
        field_name: Field name used in error messages

    Returns:
        Decimal-coerced value

    Raises:
        InvalidStrategyError: If the value cannot be coerced to a finite Decimal
    """
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidStrategyError(f"'{field_name}' must be a finite number")
        return value
    if isinstance(value, bool):
        # bool is a subclass of int in Python; reject it explicitly.
        raise InvalidStrategyError(f"'{field_name}' must be a number, got bool")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # Use string conversion to avoid binary-float artefacts.
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise InvalidStrategyError(
                f"'{field_name}' is not a valid number: {value!r}"
            ) from exc
        if not result.is_finite():
            raise InvalidStrategyError(f"'{field_name}' must be a finite number")
        return result
    if isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise InvalidStrategyError(
                f"'{field_name}' is not a valid number: {value!r}"
            ) from exc
        if not result.is_finite():
            raise InvalidStrategyError(f"'{field_name}' must be a finite number")
        return result
    raise InvalidStrategyError(
        f"'{field_name}' must be a number, got {type(value).__name__}"
    )


def _parse_allocation(raw: object) -> dict[str, Decimal]:
    """Validate and parse an allocation mapping.

    Args:
        raw: Raw value (expected to be a non-empty dict of ticker → fraction)

    Returns:
        Dictionary of ticker → fraction (Decimal)

    Raises:
        InvalidStrategyError: If the allocation is missing, empty, has invalid
            keys/values, or its fractions do not sum to ~1.0.
    """
    if not isinstance(raw, dict) or not raw:
        raise InvalidStrategyError(
            "'allocation' must be a non-empty mapping of ticker to fraction"
        )

    parsed: dict[str, Decimal] = {}
    for ticker, fraction in raw.items():
        if not isinstance(ticker, str) or not ticker:
            raise InvalidStrategyError(
                "'allocation' keys must be non-empty ticker strings"
            )
        decimal_fraction = _coerce_decimal(fraction, f"allocation[{ticker}]")
        if decimal_fraction < Decimal("0") or decimal_fraction > Decimal("1"):
            raise InvalidStrategyError(
                f"allocation[{ticker}] must be between 0 and 1, got {decimal_fraction}"
            )
        parsed[ticker] = decimal_fraction

    total = sum(parsed.values(), Decimal("0"))
    if abs(total - Decimal("1")) > _ALLOCATION_SUM_TOLERANCE:
        raise InvalidStrategyError(
            f"allocation values must sum to 1.0 (got {total:.4f})"
        )
    return parsed


def _allocation_to_dict(allocation: Mapping[str, Decimal]) -> dict[str, str]:
    """Serialize an allocation mapping to JSON-friendly strings."""
    return {ticker: str(fraction) for ticker, fraction in allocation.items()}


@dataclass(frozen=True)
class BuyAndHoldParameters:
    """Parameters for a ``BUY_AND_HOLD`` strategy.

    Attributes:
        allocation: Mapping of ticker → fraction-of-cash (must sum to ~1.0,
            each fraction in [0, 1]).

    Raises:
        InvalidStrategyError: If the allocation is invalid.
    """

    allocation: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        """Validate parameters and normalize allocation as immutable dict."""
        # Re-parse to enforce invariants even when constructed directly.
        # ``_parse_allocation`` raises InvalidStrategyError on any violation.
        parsed = _parse_allocation(dict(self.allocation))
        # Replace with a fresh dict to ensure independent ownership.
        object.__setattr__(self, "allocation", parsed)

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dict.

        Returns:
            Dict with string-encoded Decimal fractions for stable JSON.
        """
        return {"allocation": _allocation_to_dict(self.allocation)}

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "BuyAndHoldParameters":
        """Construct from a JSON-loaded mapping.

        Args:
            raw: Mapping with at least an ``allocation`` key.

        Returns:
            Validated ``BuyAndHoldParameters`` instance.

        Raises:
            InvalidStrategyError: If the mapping is missing required fields or
                contains invalid values.
        """
        return cls(allocation=_parse_allocation(raw.get("allocation")))


@dataclass(frozen=True)
class DcaParameters:
    """Parameters for a ``DOLLAR_COST_AVERAGING`` strategy.

    Attributes:
        frequency_days: Number of days between purchases (1–365).
        amount_per_period: USD amount invested each period (must be > 0).
        allocation: Mapping of ticker → fraction (must sum to ~1.0).

    Raises:
        InvalidStrategyError: If any field is invalid.
    """

    frequency_days: int
    amount_per_period: Decimal
    allocation: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        """Validate parameters and normalize allocation as immutable dict.

        ``isinstance(x, bool)`` is the only runtime type check that survives
        strict typing — ``bool`` is a subclass of ``int`` in Python, so the
        type system happily accepts ``DcaParameters(frequency_days=True)``.
        Reject that explicitly.
        """
        if isinstance(self.frequency_days, bool):
            raise InvalidStrategyError(
                "'frequency_days' must be an integer between 1 and 365"
            )
        if not (1 <= self.frequency_days <= 365):
            raise InvalidStrategyError(
                "'frequency_days' must be an integer between 1 and 365"
            )
        if not self.amount_per_period.is_finite():
            raise InvalidStrategyError("'amount_per_period' must be a finite number")
        if self.amount_per_period <= Decimal("0"):
            raise InvalidStrategyError("'amount_per_period' must be > 0")

        parsed = _parse_allocation(dict(self.allocation))
        object.__setattr__(self, "allocation", parsed)

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dict."""
        return {
            "frequency_days": self.frequency_days,
            "amount_per_period": str(self.amount_per_period),
            "allocation": _allocation_to_dict(self.allocation),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "DcaParameters":
        """Construct from a JSON-loaded mapping.

        Args:
            raw: Mapping with ``frequency_days``, ``amount_per_period``,
                ``allocation`` keys.

        Returns:
            Validated ``DcaParameters`` instance.

        Raises:
            InvalidStrategyError: If the mapping is missing required fields or
                contains invalid values.
        """
        frequency_raw = raw.get("frequency_days")
        if not isinstance(frequency_raw, int) or isinstance(frequency_raw, bool):
            raise InvalidStrategyError(
                "'frequency_days' must be an integer between 1 and 365"
            )

        amount_raw = raw.get("amount_per_period")
        if amount_raw is None:
            raise InvalidStrategyError("'amount_per_period' is required")
        amount = _coerce_decimal(amount_raw, "amount_per_period")

        return cls(
            frequency_days=frequency_raw,
            amount_per_period=amount,
            allocation=_parse_allocation(raw.get("allocation")),
        )


@dataclass(frozen=True)
class MaCrossoverParameters:
    """Parameters for a ``MOVING_AVERAGE_CROSSOVER`` strategy.

    Attributes:
        fast_window: Short-term SMA window in trading days (2–200).
        slow_window: Long-term SMA window in trading days (2–200, must be
            strictly greater than ``fast_window``).
        invest_fraction: Fraction of cash to invest on a BUY signal (0 < f ≤ 1).

    Raises:
        InvalidStrategyError: If any field is invalid.
    """

    fast_window: int
    slow_window: int
    invest_fraction: Decimal

    def __post_init__(self) -> None:
        """Validate parameters.

        ``isinstance(x, bool)`` is the only runtime type check that survives
        strict typing — ``bool`` is a subclass of ``int`` in Python, so the
        type system accepts ``MaCrossoverParameters(fast_window=True, ...)``.
        Reject that explicitly.
        """
        for name, value in (
            ("fast_window", self.fast_window),
            ("slow_window", self.slow_window),
        ):
            if isinstance(value, bool):
                raise InvalidStrategyError(
                    f"'{name}' must be an integer between 2 and 200"
                )
            if not (2 <= value <= 200):
                raise InvalidStrategyError(
                    f"'{name}' must be an integer between 2 and 200"
                )
        if self.fast_window >= self.slow_window:
            raise InvalidStrategyError("'fast_window' must be less than 'slow_window'")

        if not self.invest_fraction.is_finite():
            raise InvalidStrategyError("'invest_fraction' must be a finite number")
        if not (Decimal("0") < self.invest_fraction <= Decimal("1")):
            raise InvalidStrategyError("'invest_fraction' must be > 0 and <= 1.0")

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-friendly dict."""
        return {
            "fast_window": self.fast_window,
            "slow_window": self.slow_window,
            "invest_fraction": str(self.invest_fraction),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "MaCrossoverParameters":
        """Construct from a JSON-loaded mapping.

        Args:
            raw: Mapping with ``fast_window``, ``slow_window``,
                ``invest_fraction`` keys.

        Returns:
            Validated ``MaCrossoverParameters`` instance.

        Raises:
            InvalidStrategyError: If the mapping is missing required fields or
                contains invalid values.
        """
        fast_raw = raw.get("fast_window")
        slow_raw = raw.get("slow_window")
        if not isinstance(fast_raw, int) or isinstance(fast_raw, bool):
            raise InvalidStrategyError(
                "'fast_window' must be an integer between 2 and 200"
            )
        if not isinstance(slow_raw, int) or isinstance(slow_raw, bool):
            raise InvalidStrategyError(
                "'slow_window' must be an integer between 2 and 200"
            )

        invest_raw = raw.get("invest_fraction")
        if invest_raw is None:
            raise InvalidStrategyError("'invest_fraction' is required")
        invest = _coerce_decimal(invest_raw, "invest_fraction")

        return cls(
            fast_window=fast_raw,
            slow_window=slow_raw,
            invest_fraction=invest,
        )


# Discriminated-union type alias. The discriminator is ``Strategy.strategy_type``;
# downstream code matches via ``isinstance`` or ``match`` statements on the
# concrete subtype (Pyright sees each branch as a single concrete dataclass).
type StrategyParameters = BuyAndHoldParameters | DcaParameters | MaCrossoverParameters


_PARAMETERS_BY_TYPE: dict[
    StrategyType,
    type[BuyAndHoldParameters] | type[DcaParameters] | type[MaCrossoverParameters],
] = {
    StrategyType.BUY_AND_HOLD: BuyAndHoldParameters,
    StrategyType.DOLLAR_COST_AVERAGING: DcaParameters,
    StrategyType.MOVING_AVERAGE_CROSSOVER: MaCrossoverParameters,
}


def parameters_from_dict(
    strategy_type: StrategyType, raw: Mapping[str, object]
) -> StrategyParameters:
    """Parse a JSON-loaded parameter mapping into the typed dataclass.

    Args:
        strategy_type: Discriminator selecting the concrete parameter type.
        raw: Raw parameter mapping (e.g. from an API request body or a JSON
            DB column).

    Returns:
        Validated ``StrategyParameters`` instance of the appropriate concrete
        subtype.

    Raises:
        InvalidStrategyError: If the mapping is missing required fields or
            contains invalid values.
    """
    params_cls = _PARAMETERS_BY_TYPE.get(strategy_type)
    if params_cls is None:
        raise InvalidStrategyError(
            f"Strategy type not supported: {strategy_type.value}"
        )
    return params_cls.from_dict(raw)


def parameters_for_type(
    strategy_type: StrategyType, params: StrategyParameters
) -> bool:
    """Check whether the given typed parameters match the strategy type.

    Args:
        strategy_type: Strategy type discriminator
        params: Typed parameter instance

    Returns:
        True if ``params`` is the concrete dataclass expected for
        ``strategy_type``.
    """
    expected = _PARAMETERS_BY_TYPE.get(strategy_type)
    return expected is not None and isinstance(params, expected)
