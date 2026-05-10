"""Pure-function evaluators for each :class:`ConditionType`.

Each evaluator is a pure function — no I/O, no side effects — that takes
fully-resolved inputs (the trigger, its activation, the portfolio's
ledger-derived state, the relevant market data) and returns ``(fired,
evaluation_data)``. The composing :class:`TriggerEvaluationService` is
responsible for the I/O upstream of the call.

The :func:`evaluate_earnings_proximity` evaluator is a small exception:
it takes the :class:`EarningsCalendarPort` directly (per design §2.1.4)
because the port is its only consumer and the alternative — fetching
events upstream and passing them in — bloats the service for no
benefit.

Phase F evaluators:

- F-2: :func:`evaluate_drawdown` — landed in PR #261.
- F-4: :func:`evaluate_volatility_spike` and
  :func:`evaluate_earnings_proximity` — this PR.
- ``CUSTOM_RULE`` is intentionally not implemented (Phase F design Q1).
"""

from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluationData,
    DrawdownEvaluatorInput,
    PortfolioValuePoint,
    evaluate_drawdown,
)
from zebu.application.services.trigger_evaluators.earnings_proximity import (
    EarningsEvaluationData,
    EarningsEvaluatorInput,
    evaluate_earnings_proximity,
)
from zebu.application.services.trigger_evaluators.volatility_spike import (
    TickerClose,
    VolatilityEvaluationData,
    VolatilityEvaluatorInput,
    evaluate_volatility_spike,
)

__all__ = [
    "DrawdownEvaluationData",
    "DrawdownEvaluatorInput",
    "EarningsEvaluationData",
    "EarningsEvaluatorInput",
    "PortfolioValuePoint",
    "TickerClose",
    "VolatilityEvaluationData",
    "VolatilityEvaluatorInput",
    "evaluate_drawdown",
    "evaluate_earnings_proximity",
    "evaluate_volatility_spike",
]
