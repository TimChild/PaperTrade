"""Domain layer exceptions.

All domain exceptions inherit from DomainException to allow catching all domain errors.
These exceptions represent business rule violations and invalid domain states.
"""


class DomainException(Exception):
    """Base exception for all domain layer errors."""

    pass


# Value Object Exceptions


class InvalidValueObjectError(DomainException):
    """Base exception for invalid value object construction."""

    pass


class InvalidMoneyError(InvalidValueObjectError):
    """Raised when Money value object construction or operation fails."""

    pass


class InvalidTickerError(InvalidValueObjectError):
    """Raised when Ticker value object validation fails."""

    pass


class InvalidQuantityError(InvalidValueObjectError):
    """Raised when Quantity value object validation fails."""

    pass


class InvalidTradeSignalError(InvalidValueObjectError):
    """Raised when TradeSignal value object construction or validation fails."""

    pass


class InvalidAllocationError(InvalidValueObjectError):
    """Raised when Allocation value object construction or validation fails."""

    pass


# Entity Exceptions


class InvalidEntityError(DomainException):
    """Base exception for invalid entity construction."""

    pass


class InvalidPortfolioError(InvalidEntityError):
    """Raised when Portfolio entity invariants are violated."""

    pass


class PortfolioNotFoundError(InvalidEntityError):
    """Raised when a portfolio cannot be found by ID."""

    def __init__(self, portfolio_id: str) -> None:
        """Initialize PortfolioNotFoundError.

        Args:
            portfolio_id: ID of the portfolio that was not found
        """
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio not found: {portfolio_id}")


class InvalidTransactionError(InvalidEntityError):
    """Raised when Transaction entity invariants are violated."""

    pass


class InvalidStrategyError(InvalidEntityError):
    """Raised when Strategy entity invariants are violated."""

    pass


class InvalidBacktestRunError(InvalidEntityError):
    """Raised when BacktestRun entity invariants are violated."""

    pass


class InvalidStrategyActivationError(InvalidEntityError):
    """Raised when StrategyActivation entity invariants are violated."""

    pass


class InvalidApiKeyError(InvalidEntityError):
    """Raised when ApiKey entity invariants are violated."""

    pass


class InvalidTriggerError(InvalidEntityError):
    """Raised when StrategyConditionTrigger or its condition params invariants
    are violated.

    Used for both entity-level checks (e.g. status / lifecycle errors,
    timestamp invariants) and value-object-level checks (a typed condition
    param whose fields are out of range, or a ``CUSTOM_RULE`` construction
    while that variant remains deliberately unimplemented).
    """

    pass


class InvalidTriggerFireError(InvalidEntityError):
    """Raised when TriggerFireRecord invariants are violated.

    The fire record has cross-field constraints (exactly one of the three
    "resulting" pointers is set unless the response is HOLD or
    INVOCATION_FAILED), and a few timestamp / latency rules. Surface as a
    distinct exception so callers can differentiate "trigger configuration
    is bad" from "fire record is bad" in audit-trail handling.
    """

    pass


class InvalidBacktestAgentInvocationError(InvalidEntityError):
    """Raised when BacktestAgentInvocation invariants are violated.

    The backtest invocation row has per-mode cross-field constraints
    (MOCK rows have empty rationale / no payload; LIVE rows must carry a
    decision and a model identifier; ``decision_executed`` is only valid
    for actionable LIVE decisions). Distinct from :class:`InvalidTriggerFireError`
    so callers can differentiate "live audit row is bad" from "simulated
    audit row is bad" — the two entities have similar shape but different
    rules.
    """

    pass


class AgentInvocationError(DomainException):
    """Raised when invoking an agent through :class:`AgentInvocationPort` fails.

    Used for transport failures (network errors, timeouts), authentication
    failures (missing or invalid Anthropic API key), and protocol failures
    (the agent's response can't be parsed as a structured decision). The
    trigger-invocation orchestrator catches this and writes an
    ``INVOCATION_FAILED`` :class:`TriggerFireRecord` so the activity feed
    surfaces the failed attempt rather than dropping it silently.

    Attributes:
        message: Human-readable error description.
        cause: Optional underlying exception (e.g. the Anthropic SDK error).
    """

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        """Initialise with a message and optional underlying cause."""
        super().__init__(message)
        self.message = message
        self.cause = cause


class AgentResponseParseError(AgentInvocationError):
    """Raised when an agent response cannot be coerced into a structured decision.

    Distinct subclass so callers (and structured-logging middleware) can
    differentiate "the model returned malformed output" from "the call
    itself failed". Both paths still produce ``INVOCATION_FAILED`` audit
    rows, but the operational response differs (parse failures usually
    indicate prompt regression; transport failures indicate infra issues).
    """

    pass


class BacktestSafetyViolationError(AgentInvocationError):
    """Raised when a backtest agent invocation violates the safety contract.

    The :class:`BacktestAgentInvocationAdapter` (Phase L-2) enforces two
    invariants on every tool call the agent issues:

    1. The tool name MUST be in :class:`BacktestSafeTool` (the
       ``BACKTEST_SAFE_TOOLS`` whitelist). Anything else — ``web_search``,
       ``fetch_news``, ``get_current_price``, third-party MCP tools, etc.
       — is rejected.
    2. Any date or datetime argument MUST be at or before
       ``simulated_date`` end-of-UTC-day. Future-data leakage is the #1
       backtest pitfall.

    Raising this exception is the adapter's only response to a violation
    — it never silently coerces the argument, never substitutes a safe
    default — so the L-3 executor records the broken-contract signal as
    an ``INVOCATION_FAILED`` audit row with the reason on
    ``BacktestAgentInvocation.rationale``.

    Distinct from :class:`AgentResponseParseError` because the model's
    response was structurally valid — the agent emitted a parseable
    tool-use block — it just chose an unsafe target. Operationally, a
    parse error indicates a prompt regression; a safety violation
    indicates the agent ignored the backtest-mode preamble (or attempted
    an unconstrained generation despite the schema constraint).

    Attributes:
        tool_name: Name of the offending tool. ``None`` when the violation
            is not tool-bound (e.g. an unbound parameter check).
        simulated_date: The in-simulation calendar day that bounds the
            permissible data window. Carried for L-3's audit-row writer
            so the rationale captures the exact date the agent tried to
            exceed.
        reason: Human-readable description of what went wrong (e.g.
            ``"end date 2024-03-16 exceeds simulated_date 2024-03-15"``).
    """

    def __init__(
        self,
        *,
        tool_name: str | None,
        simulated_date: "date",  # type: ignore  # Forward ref to keep stdlib import deferred  # noqa: F821
        reason: str,
    ) -> None:
        """Initialise the violation with the offending tool + reason.

        Args:
            tool_name: Name of the tool the agent attempted to call.
                ``None`` when the violation is not tool-bound.
            simulated_date: The simulated-day boundary that was exceeded.
            reason: Human-readable description of the violation; lands on
                ``BacktestAgentInvocation.rationale`` via the L-3
                executor.
        """
        self.tool_name = tool_name
        self.simulated_date = simulated_date
        self.reason = reason
        message = (
            f"Backtest safety violation"
            f"{f' on tool {tool_name!r}' if tool_name is not None else ''}"
            f" (simulated_date={simulated_date.isoformat()}): {reason}"
        )
        super().__init__(message)


# Business Rule Violation Exceptions


class BusinessRuleViolationError(DomainException):
    """Base exception for business rule violations."""

    pass


class InsufficientFundsError(BusinessRuleViolationError):
    """Raised when attempting to withdraw more cash than available.

    Attributes:
        available: Amount of cash currently available
        required: Amount of cash needed for the operation
        message: Human-readable error message
    """

    def __init__(
        self,
        available: "Money",  # type: ignore  # Forward reference to avoid circular import  # noqa: F821
        required: "Money",  # type: ignore  # noqa: F821
        message: str | None = None,
    ) -> None:
        """Initialize InsufficientFundsError with amount details.

        Args:
            available: Amount currently available
            required: Amount needed
            message: Optional custom message (auto-generated if not provided)
        """
        from zebu.domain.value_objects.money import Money

        if not isinstance(available, Money):
            raise TypeError(f"available must be Money, got {type(available)}")
        if not isinstance(required, Money):
            raise TypeError(f"required must be Money, got {type(required)}")
        if available.currency != required.currency:
            raise ValueError("available and required must have same currency")

        self.available = available
        self.required = required

        if message is None:
            shortfall = required.subtract(available)
            message = (
                f"Insufficient funds. You have {available} but need {required} "
                f"for this trade (shortfall: {shortfall})"
            )

        self.message = message
        super().__init__(message)


class InsufficientSharesError(BusinessRuleViolationError):
    """Raised when attempting to sell more shares than owned.

    Attributes:
        ticker: Stock ticker symbol
        available: Number of shares currently owned
        required: Number of shares needed for the sale
        message: Human-readable error message
    """

    def __init__(
        self,
        ticker: str,
        available: "Quantity",  # type: ignore  # Forward reference  # noqa: F821
        required: "Quantity",  # type: ignore  # noqa: F821
        message: str | None = None,
    ) -> None:
        """Initialize InsufficientSharesError with share details.

        Args:
            ticker: Stock ticker symbol
            available: Shares currently owned
            required: Shares needed for sale
            message: Optional custom message (auto-generated if not provided)
        """
        from zebu.domain.value_objects.quantity import Quantity

        if not isinstance(available, Quantity):
            raise TypeError(f"available must be Quantity, got {type(available)}")
        if not isinstance(required, Quantity):
            raise TypeError(f"required must be Quantity, got {type(required)}")

        self.ticker = ticker
        self.available = available
        self.required = required

        if message is None:
            shortfall = required.shares - available.shares
            message = (
                f"Insufficient shares of {ticker}. You have {available.shares} shares "
                f"but need {required.shares} shares (shortfall: {shortfall})"
            )

        self.message = message
        super().__init__(message)


class InsufficientHistoricalDataError(BusinessRuleViolationError):
    """Raised when historical price data is missing for a backtest.

    Attributes:
        ticker: The ticker with missing data
        message: Human-readable error description
    """

    def __init__(self, ticker: str, message: str | None = None) -> None:
        """Initialize InsufficientHistoricalDataError.

        Args:
            ticker: The ticker symbol with no available price data
            message: Optional custom error message
        """
        self.ticker = ticker
        if message is None:
            message = f"No historical price data available for ticker: {ticker}"
        super().__init__(message)


# Authentication Exceptions


class AuthenticationError(DomainException):
    """Base exception for authentication-related errors."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid, expired, or malformed."""

    pass
