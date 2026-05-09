"""Standard error envelope for all API responses.

Wave 3-G: This module defines the single error response shape every route in
Zebu must emit. The audit (`agent_docs/audits/2026-05-09/api-design.md` finding
P1-API-4) found that `detail` was sometimes a string and sometimes a structured
dict, forcing every consumer to branch on `typeof detail` to read the message.

The new envelope is:

    {
        "detail": "<human-readable string>",
        "code": "<optional machine-readable code>",
        "fields": {"<field_name>": "<message>", ...} | null
    }

`detail` is always a string. `code` carries the machine-readable identifier
that previously lived in `detail.type` (e.g. ``insufficient_funds``,
``ticker_not_found``). Anything that previously rode along inside the dict
detail (`available`, `required`, `shortfall`, `ticker`, `reason`, ...) goes
into ``fields`` as string values so a single map fits all error types and the
OpenAPI schema does not have to enumerate them.

`fields` doubles as the per-field validation map for 422 responses: each
``loc`` from FastAPI's `RequestValidationError` becomes a ``fields`` entry.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Machine-readable error codes shared across routes.

    Values are stable strings — frontend / MCP clients can match on these.
    Add a new entry here whenever a new domain exception is mapped, rather
    than passing a free-form string to ``ErrorResponse(code=...)``.
    """

    # Domain — funds and shares
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INSUFFICIENT_SHARES = "insufficient_shares"

    # Domain — value-object validation
    INVALID_TICKER = "invalid_ticker"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_MONEY = "invalid_money"
    INVALID_PORTFOLIO = "invalid_portfolio"
    INVALID_TRANSACTION = "invalid_transaction"
    INVALID_STRATEGY = "invalid_strategy"
    INVALID_EXPLORATION_TASK = "invalid_exploration_task"

    # Application — market data
    TICKER_NOT_FOUND = "ticker_not_found"
    MARKET_DATA_UNAVAILABLE = "market_data_unavailable"
    INSUFFICIENT_HISTORICAL_DATA = "insufficient_historical_data"

    # Resource lookup
    PORTFOLIO_NOT_FOUND = "portfolio_not_found"
    STRATEGY_NOT_FOUND = "strategy_not_found"
    BACKTEST_NOT_FOUND = "backtest_not_found"

    # Authorization
    FORBIDDEN = "forbidden"
    UNAUTHENTICATED = "unauthenticated"

    # Generic
    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(BaseModel):
    """Standard error envelope returned for every error response.

    Attributes:
        detail: Human-readable message describing what went wrong. Always a
            string. Frontend can show this directly without further parsing.
        code: Optional machine-readable error code. Use the values from
            ``ErrorCode`` when an existing code matches; otherwise add a new
            enum member rather than passing a free-form string. ``None`` for
            generic errors that do not need to be branched on.
        fields: Optional per-field detail map. For 422 validation errors this
            holds ``{field_name: error_message}`` entries. For domain errors
            this carries auxiliary data such as ``available`` /
            ``required`` / ``shortfall`` / ``ticker`` / ``reason``. All
            values are strings — clients parse to the expected type.
    """

    detail: str
    code: str | None = None
    fields: dict[str, str] | None = Field(default=None)
