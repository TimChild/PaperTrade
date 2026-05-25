"""Port for validating that a ticker is recognised by the market-data provider.

The port is declared here (application layer) so the domain and use-case
code can depend on the abstraction without importing the concrete AV
adapter. The implementation lives in
``adapters/outbound/market_data/av_ticker_validator.py``.
"""

from __future__ import annotations

from typing import Protocol

from zebu.domain.value_objects.ticker import Ticker


class TickerValidatorPort(Protocol):
    """Check whether a ticker symbol is recognised by the data provider.

    Implementations must call a cheap, real-time provider endpoint (e.g.
    Alpha Vantage ``GLOBAL_QUOTE``) to confirm the symbol exists. They
    must **not** swallow rate-limit or network errors as ``False`` — the
    caller (``POST /admin/watchlist``) needs to distinguish "provider
    doesn't know this symbol" (→ 422) from "we couldn't reach the
    provider" (→ 500) to avoid silently accepting bogus tickers when the
    network is down.
    """

    async def is_recognised(self, ticker: Ticker) -> bool:
        """Return ``True`` if the provider recognises the ticker symbol.

        Args:
            ticker: The ticker to validate.

        Returns:
            ``True`` when the provider returns a non-empty quote for the
            ticker. ``False`` when the provider's response indicates the
            symbol is unknown (e.g. Alpha Vantage returns an empty
            ``Global Quote`` object).

        Raises:
            MarketDataUnavailableError: When the provider is temporarily
                unreachable (rate-limit hit, network error, etc.). The
                caller should surface this as a 500 rather than a 422.
        """
        ...
