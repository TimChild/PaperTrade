"""Pure-function evaluators for each :class:`ConditionType`.

Each evaluator is a pure function — no I/O, no side effects — that takes
fully-resolved inputs (the trigger, its activation, the portfolio's
ledger-derived state, the relevant market data) and returns ``(fired,
evaluation_data)``. The composing :class:`TriggerEvaluationService` is
responsible for the I/O upstream of the call.

F-2 ships :func:`evaluate_drawdown` only. F-4 will add ``evaluate_volatility``
and ``evaluate_earnings`` alongside.
"""

from zebu.application.services.trigger_evaluators.drawdown import (
    DrawdownEvaluationData,
    DrawdownEvaluatorInput,
    PortfolioValuePoint,
    evaluate_drawdown,
)

__all__ = [
    "DrawdownEvaluationData",
    "DrawdownEvaluatorInput",
    "PortfolioValuePoint",
    "evaluate_drawdown",
]
