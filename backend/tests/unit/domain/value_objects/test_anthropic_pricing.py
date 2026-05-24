"""Unit tests for the Phase L-6 Anthropic pricing module.

Exercises:

* Per-model lookup (known + unknown).
* Unknown-model fallback logs a warning and behaves as Haiku-4.5.
* Token-to-USD math.
* Negative token clamping (defensive).
"""

from __future__ import annotations

import logging
from decimal import Decimal

import pytest

from zebu.domain.value_objects.anthropic_pricing import (
    ModelPricing,
    estimate_cost_usd,
    get_pricing,
)


class TestGetPricing:
    """Per-model lookup and fallback semantics."""

    def test_known_haiku_model_returns_published_pricing(self) -> None:
        """Haiku-4.5 rates match Anthropic's public 2026-05 pricing page."""
        pricing = get_pricing("claude-haiku-4-5-20251001")
        assert pricing == ModelPricing(
            input_per_mtok=Decimal("0.80"),
            output_per_mtok=Decimal("4.00"),
        )

    def test_known_sonnet_model_returns_published_pricing(self) -> None:
        """Sonnet-4.5 rates match Anthropic's public 2026-05 pricing page."""
        pricing = get_pricing("claude-sonnet-4-5-20250929")
        assert pricing == ModelPricing(
            input_per_mtok=Decimal("3.00"),
            output_per_mtok=Decimal("15.00"),
        )

    def test_known_opus_model_returns_published_pricing(self) -> None:
        """Opus-4 rates match Anthropic's public 2026-05 pricing page."""
        pricing = get_pricing("claude-opus-4-20250514")
        assert pricing == ModelPricing(
            input_per_mtok=Decimal("15.00"),
            output_per_mtok=Decimal("75.00"),
        )

    def test_unknown_model_falls_back_to_haiku_pricing(self) -> None:
        """Unknown identifiers return Haiku-4.5 rates so the executor doesn't crash."""
        fallback = get_pricing("claude-future-9999-99999999")
        haiku = get_pricing("claude-haiku-4-5-20251001")
        assert fallback == haiku

    def test_unknown_model_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Unknown-model lookup emits a WARNING with the bad identifier."""
        with caplog.at_level(
            logging.WARNING, logger="zebu.domain.value_objects.anthropic_pricing"
        ):
            get_pricing("claude-mystery-9999")
        assert any(
            "claude-mystery-9999" in record.message for record in caplog.records
        ), "Warning should mention the unknown model identifier"
        assert any(record.levelname == "WARNING" for record in caplog.records)


class TestEstimateCostUsd:
    """Token-to-USD math and edge cases."""

    def test_haiku_one_million_input_tokens_costs_dollar_eighty(self) -> None:
        """1M input tokens × $0.80/MTok = $0.80."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        assert cost == Decimal("0.80")

    def test_haiku_one_million_output_tokens_costs_four_dollars(self) -> None:
        """1M output tokens × $4.00/MTok = $4.00."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=1_000_000,
        )
        assert cost == Decimal("4.00")

    def test_haiku_mixed_input_output_sums(self) -> None:
        """Cost is sum of input + output components."""
        # 500k input × $0.80 + 250k output × $4.00 = $0.40 + $1.00 = $1.40
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=500_000,
            output_tokens=250_000,
        )
        assert cost == Decimal("1.40")

    def test_haiku_small_token_count_produces_fractional_cost(self) -> None:
        """1000 input + 500 output @ Haiku → small fractional cost."""
        # 1000 / 1M * 0.80 + 500 / 1M * 4.00 = 0.0008 + 0.002 = 0.0028
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost == Decimal("0.0028")

    def test_zero_tokens_yields_zero_cost(self) -> None:
        """Zero tokens → zero cost (test fakes returning no usage)."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == Decimal("0")

    def test_negative_input_tokens_clamped_to_zero(self) -> None:
        """Negative token counts are clamped, preventing budget leakage."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=-1000,
            output_tokens=500,
        )
        # Only the 500 output tokens should be billed.
        assert cost == Decimal("0.002")

    def test_negative_output_tokens_clamped_to_zero(self) -> None:
        """Negative output tokens are also clamped to zero."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=-500,
        )
        assert cost == Decimal("0.0008")

    def test_unknown_model_uses_haiku_pricing_for_cost(self) -> None:
        """Unknown model → Haiku-4.5 pricing applied to the same token counts."""
        unknown_cost = estimate_cost_usd(
            model="claude-mystery-9999",
            input_tokens=500_000,
            output_tokens=250_000,
        )
        haiku_cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=500_000,
            output_tokens=250_000,
        )
        assert unknown_cost == haiku_cost

    def test_unknown_model_does_not_raise(self) -> None:
        """The estimator never raises on unknown models — just warns + falls back."""
        # Should not raise.
        cost = estimate_cost_usd(
            model="future-unknown-model-id",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost > Decimal("0")

    def test_sonnet_costs_higher_than_haiku_for_same_tokens(self) -> None:
        """Sanity: Sonnet pricing > Haiku pricing for identical workload."""
        haiku = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=100_000,
            output_tokens=10_000,
        )
        sonnet = estimate_cost_usd(
            model="claude-sonnet-4-5-20250929",
            input_tokens=100_000,
            output_tokens=10_000,
        )
        assert sonnet > haiku

    def test_cache_read_input_tokens_billed_at_ten_percent_of_input_rate(
        self,
    ) -> None:
        """1M cache-read tokens at Haiku = 0.1 × $0.80 = $0.08."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=0,
            cache_read_input_tokens=1_000_000,
        )
        assert cost == Decimal("0.080")

    def test_cache_creation_input_tokens_billed_at_one_twenty_five_input_rate(
        self,
    ) -> None:
        """1M cache-creation tokens at Haiku = 1.25 × $0.80 = $1.00."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=0,
            cache_creation_input_tokens=1_000_000,
        )
        assert cost == Decimal("1.000")

    def test_full_token_breakdown_sums_all_buckets(self) -> None:
        """All four buckets compose additively; regression for the
        bug where cache-read/creation tokens were silently dropped from
        the cost accumulator (would have under-billed by 5-25% on
        cache-heavy workloads).
        """
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,  # $0.80
            output_tokens=1_000_000,  # $4.00
            cache_read_input_tokens=1_000_000,  # $0.08
            cache_creation_input_tokens=1_000_000,  # $1.00
        )
        # 0.80 + 4.00 + 0.08 + 1.00 = 5.88
        assert cost == Decimal("5.880")

    def test_negative_cache_tokens_clamped_to_zero(self) -> None:
        """Defensive: negative cache-read / cache-creation are clamped."""
        cost = estimate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=0,
            cache_read_input_tokens=-500_000,
            cache_creation_input_tokens=-500_000,
        )
        assert cost == Decimal("0")
