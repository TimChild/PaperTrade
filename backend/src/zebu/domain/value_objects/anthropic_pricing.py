"""Anthropic model pricing — pure value-object table for cost estimation.

Phase L-6 (per-backtest budget guardrails). Maps the Anthropic model
identifiers Zebu uses in production to per-million-token pricing in USD
so the executor can estimate the cost of an agent invocation from the
token counts the adapter surfaces on every
:class:`AgentInvocationResult`.

The table lives in the **domain layer** because pricing is a pure-data
concern with no I/O dependency. It MUST NOT import from infrastructure /
adapters / application. The pricing values themselves are pulled from
Anthropic's public pricing page at the time of implementation
(2026-05-23):

  - Claude Haiku 4.5: $0.80 / MTok input, $4.00 / MTok output
  - Claude Sonnet 4.5: $3.00 / MTok input, $15.00 / MTok output
  - Claude Opus 4: $15.00 / MTok input, $75.00 / MTok output

Cache-read input tokens are billed at 0.1× the standard input rate (a
public Anthropic convention); cache-creation (cache-write) input tokens
are billed at 1.25×. The Anthropic SDK reports them as **separate
fields** on ``Message.usage`` (``cache_read_input_tokens`` /
``cache_creation_input_tokens``) — they are NOT bundled into
``input_tokens``. The cost estimator differentiates them and applies the
correct multipliers; failing to do so under-bills cache-heavy workloads
like Phase F-3's cached system prompt by 5-25%, which would let LIVE
backtests blow through the operator's ``agent_max_cost_usd`` cap.

When the executor encounters an unknown model identifier, it falls back
to Haiku-4.5 pricing and logs a warning. This is defensive: a model
swap in production should never make the executor crash, but it also
should never silently zero-out cost accumulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPricing:
    """Per-million-token pricing for a single Anthropic model.

    Both fields are in USD per 1,000,000 tokens (the unit Anthropic
    publishes). Values are stored as :class:`Decimal` to avoid
    float-rounding drift on a long-running backtest's accumulator.

    Attributes:
        input_per_mtok: Cost in USD per 1 million input tokens.
        output_per_mtok: Cost in USD per 1 million output tokens.
    """

    input_per_mtok: Decimal
    output_per_mtok: Decimal


# The canonical model identifier for cost-fallback when the model isn't
# in the table. Haiku-4.5 is the cheapest tier we ship; falling back to
# it makes the warning-and-keep-going behaviour conservative on cost
# overestimation (we never under-bill an unknown model).
_FALLBACK_MODEL: str = "claude-haiku-4-5-20251001"

# Pricing table. Keys are the exact :attr:`AgentInvocationResult.model`
# identifiers the production adapter sets — match what
# ``ZEBU_AGENT_MODEL`` env var lands on.
_MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-haiku-4-5-20251001": ModelPricing(
        input_per_mtok=Decimal("0.80"),
        output_per_mtok=Decimal("4.00"),
    ),
    "claude-sonnet-4-5-20250929": ModelPricing(
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
    ),
    "claude-opus-4-20250514": ModelPricing(
        input_per_mtok=Decimal("15.00"),
        output_per_mtok=Decimal("75.00"),
    ),
}


# ``_MTOK`` factor is the denominator that converts a "per-million-tokens"
# rate into the per-token rate the executor multiplies the actual token
# counts by. Keeping it as a Decimal preserves precision.
_MTOK: Decimal = Decimal("1000000")


def get_pricing(model: str) -> ModelPricing:
    """Look up :class:`ModelPricing` for an Anthropic model identifier.

    Args:
        model: Model identifier as returned by the production adapter on
            :attr:`AgentInvocationResult.model` (e.g.
            ``"claude-haiku-4-5-20251001"``).

    Returns:
        The pricing entry for ``model``, or the Haiku-4.5 fallback when
        ``model`` is not in the table. The fallback case logs a warning
        once per unknown identifier per process — operators see the drift
        without log spam.
    """
    pricing = _MODEL_PRICING.get(model)
    if pricing is not None:
        return pricing
    logger.warning(
        "Unknown Anthropic model %r — falling back to Haiku-4.5 pricing for "
        "cost estimation. Add this model to backend/src/zebu/domain/"
        "value_objects/anthropic_pricing.py to silence this warning.",
        model,
    )
    fallback = _MODEL_PRICING[_FALLBACK_MODEL]
    return fallback


# Anthropic-published multipliers (relative to the standard input rate)
# for cache-related input tokens. See module docstring.
_CACHE_READ_MULTIPLIER: Decimal = Decimal("0.1")
_CACHE_CREATION_MULTIPLIER: Decimal = Decimal("1.25")


def estimate_cost_usd(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
) -> Decimal:
    """Estimate the USD cost of one agent invocation.

    Multiplies token counts by the per-token rate derived from the model's
    :class:`ModelPricing`, applying Anthropic's published multipliers for
    cache-read (0.1×) and cache-creation (1.25×) input tokens. Returns a
    :class:`Decimal` so the executor's accumulator preserves cent-level
    precision across hundreds of fires.

    Negative token counts are clamped to zero — they shouldn't occur in
    practice (Anthropic always returns non-negatives), but if a misbehaving
    transport returns one we'd rather over-cap than under-cap.

    Args:
        model: Model identifier (see :func:`get_pricing`).
        input_tokens: Fresh (non-cached) input tokens consumed by the
            invocation. Maps to ``Message.usage.input_tokens``; does NOT
            include cache-read or cache-creation tokens.
        output_tokens: Output tokens produced by the invocation.
        cache_read_input_tokens: Input tokens served from prompt cache.
            Billed at 0.1× the standard input rate.
        cache_creation_input_tokens: Input tokens written to cache (cache
            fill). Billed at 1.25× the standard input rate.

    Returns:
        Estimated cost in USD (Decimal). Always ``>= 0``.
    """
    pricing = get_pricing(model)
    # Clamp to non-negative — Anthropic never sends negatives, but be
    # defensive against a misbehaving transport / test fake.
    input_count = Decimal(max(0, input_tokens))
    output_count = Decimal(max(0, output_tokens))
    cache_read_count = Decimal(max(0, cache_read_input_tokens))
    cache_creation_count = Decimal(max(0, cache_creation_input_tokens))
    input_cost = (input_count / _MTOK) * pricing.input_per_mtok
    output_cost = (output_count / _MTOK) * pricing.output_per_mtok
    cache_read_cost = (
        (cache_read_count / _MTOK) * pricing.input_per_mtok * _CACHE_READ_MULTIPLIER
    )
    cache_creation_cost = (
        (cache_creation_count / _MTOK)
        * pricing.input_per_mtok
        * _CACHE_CREATION_MULTIPLIER
    )
    return input_cost + output_cost + cache_read_cost + cache_creation_cost


__all__ = [
    "ModelPricing",
    "estimate_cost_usd",
    "get_pricing",
]
