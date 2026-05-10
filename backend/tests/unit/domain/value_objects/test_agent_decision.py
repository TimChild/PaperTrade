"""Smoke tests for the AgentDecision enum (Phase F-1).

The decision-execution side effects (BUY / SELL trade routing,
MODIFY_STRATEGY validation, NEEDS_HUMAN escalation, INVOCATION_FAILED
handling) ship in F-3. F-1 only validates the enum's shape so it
round-trips through the audit row's ``agent_response`` column.
"""

import pytest

from zebu.domain.value_objects.agent_decision import AgentDecision


class TestAgentDecision:
    def test_str_enum_values(self) -> None:
        """Each enum value is a stable string for DB storage."""
        assert AgentDecision.BUY.value == "BUY"
        assert AgentDecision.SELL.value == "SELL"
        assert AgentDecision.HOLD.value == "HOLD"
        assert AgentDecision.MODIFY_STRATEGY.value == "MODIFY_STRATEGY"
        assert AgentDecision.NEEDS_HUMAN.value == "NEEDS_HUMAN"
        assert AgentDecision.INVOCATION_FAILED.value == "INVOCATION_FAILED"

    def test_construct_from_string(self) -> None:
        """Strings round-trip back to the enum values."""
        assert AgentDecision("HOLD") is AgentDecision.HOLD
        assert AgentDecision("INVOCATION_FAILED") is AgentDecision.INVOCATION_FAILED

    def test_unknown_string_raises_value_error(self) -> None:
        """Adapter side guardrail — drifted rows surface as ValueError."""
        with pytest.raises(ValueError):
            AgentDecision("NOT_A_REAL_DECISION")
