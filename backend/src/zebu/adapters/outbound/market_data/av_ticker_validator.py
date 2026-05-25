"""Alpha Vantage implementation of :class:`TickerValidatorPort`.

Uses the ``GLOBAL_QUOTE`` endpoint (one cheap API call) to confirm that
a ticker symbol is recognised before we persist it to the watchlist.

Decision table for the ``GLOBAL_QUOTE`` response:

+-----------------------------+-------------------------------+
| Response                    | Action                        |
+=============================+===============================+
| Non-empty ``Global Quote``  | ``is_recognised → True``      |
| Empty ``Global Quote``      | ``is_recognised → False``     |
| ``Information``/``Note``    | raise ``MarketDataUnavailable``|
| HTTP / network error        | raise ``MarketDataUnavailable``|
+-----------------------------+-------------------------------+

The rate-limit branch raises rather than returning ``False`` so the
caller (``POST /admin/watchlist``) can surface a 500 ("couldn't validate
— try again") instead of a misleading 422 ("unrecognised ticker") that
would silently block the operator from pinning a perfectly valid ticker
during an AV rate-limit window.
"""

from __future__ import annotations

import logging

import httpx

from zebu.application.exceptions import MarketDataUnavailableError
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)

_AV_BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageTickerValidator:
    """Validate a ticker by calling AV's ``GLOBAL_QUOTE`` endpoint.

    A non-empty ``Global Quote`` block (price field present and non-zero)
    confirms the ticker is known.  An empty or absent ``Global Quote``
    block means AV doesn't recognise the symbol.

    Rate-limit / ``Information`` responses are **raised**, not swallowed,
    so the operator gets a 500 with a meaningful message rather than a
    misleading 422.

    Args:
        http_client: Shared ``httpx.AsyncClient`` (injected via dependency).
        api_key: Alpha Vantage API key.
        base_url: Override for tests / staging; defaults to production AV.
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str = _AV_BASE_URL,
        timeout: float = 5.0,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    async def is_recognised(self, ticker: Ticker) -> bool:
        """Return ``True`` when AV's ``GLOBAL_QUOTE`` knows the ticker.

        Args:
            ticker: The ticker symbol to validate.

        Returns:
            ``True`` if the ``Global Quote`` block is non-empty (i.e.
            the symbol exists in AV's database). ``False`` if AV returns
            an empty ``Global Quote`` object (unknown symbol).

        Raises:
            MarketDataUnavailableError: When AV responds with an
                ``Information`` or ``Note`` body (rate-limit or premium
                gate), or when any network / HTTP error occurs. The
                caller should propagate this as a 500 rather than a 422.
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker.symbol,
            "apikey": self._api_key,
        }

        try:
            response = await self._http_client.get(
                self._base_url,
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataUnavailableError(
                f"Timeout validating ticker {ticker.symbol}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MarketDataUnavailableError(
                f"HTTP {exc.response.status_code} validating ticker "
                f"{ticker.symbol}: {exc}"
            ) from exc
        except httpx.NetworkError as exc:
            raise MarketDataUnavailableError(
                f"Network error validating ticker {ticker.symbol}: {exc}"
            ) from exc
        except httpx.TransportError as exc:
            # Catches ProtocolError (e.g. RemoteProtocolError on malformed
            # responses) and ProxyError, which are siblings of NetworkError
            # under TransportError but are not caught by the three clauses
            # above.  All of these mean "we couldn't reach AV reliably" —
            # raise so the caller surfaces a 500, not an unhandled exception.
            raise MarketDataUnavailableError(
                f"Transport error validating ticker {ticker.symbol}: {exc}"
            ) from exc

        data: dict[str, object] = response.json()

        # AV uses "Information" or "Note" for both rate-limit and premium-
        # feature refusals.  The _is_premium_refusal heuristic from the
        # AlphaVantageAdapter distinguishes between the two, but for the
        # purposes of ticker validation either case means "we couldn't
        # verify" — raise so the caller surfaces a 500, not a 422.
        info_message = data.get("Information") or data.get("Note")
        if info_message and isinstance(info_message, str):
            logger.warning(
                "av_ticker_validator_rate_limited: ticker=%s message=%s",
                ticker.symbol,
                info_message[:200],
            )
            raise MarketDataUnavailableError(
                f"Alpha Vantage could not validate {ticker.symbol!r}: "
                f"{info_message[:300]}"
            )

        global_quote = data.get("Global Quote")

        # An empty dict ``{}`` means the symbol is unknown to AV.
        if not global_quote or not isinstance(global_quote, dict):
            logger.info("av_ticker_validator_unrecognised: ticker=%s", ticker.symbol)
            return False

        # Presence of the quote block alone is sufficient — the price
        # field can theoretically be "0.0000" for delisted instruments,
        # but for the purposes of watchlist-pin validation we accept any
        # non-empty quote as "recognised".
        logger.info("av_ticker_validator_recognised: ticker=%s", ticker.symbol)
        return True
