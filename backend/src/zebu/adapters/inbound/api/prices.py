"""Price API routes.

Provides REST endpoints for price data operations:
- Get current price for a ticker
- Get historical price data for a ticker
- Get supported tickers
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import MarketDataDep
from zebu.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from zebu.domain.value_objects.ticker import Ticker

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/prices", tags=["prices"])


# Response Models


class PricePointResponse(BaseModel):
    """Response model for a single price point."""

    ticker: str = Field(..., description="Stock ticker symbol")
    price: str = Field(..., description="Price in decimal format")
    currency: str = Field(..., description="ISO 4217 currency code")
    timestamp: datetime = Field(..., description="When price was observed (UTC)")
    source: str = Field(..., description="Data source (alpha_vantage, cache, database)")
    interval: str = Field(..., description="Price interval type")


class PriceHistoryResponse(BaseModel):
    """Response model for price history query."""

    ticker: str = Field(..., description="Stock ticker symbol")
    prices: list[PricePointResponse] = Field(..., description="List of price points")
    start: datetime = Field(..., description="Start of time range (UTC)")
    end: datetime = Field(..., description="End of time range (UTC)")
    interval: str = Field(..., description="Price interval type")
    count: int = Field(..., description="Number of price points returned")


class CurrentPriceResponse(BaseModel):
    """Response model for current price query."""

    ticker: str = Field(..., description="Stock ticker symbol")
    price: str = Field(..., description="Current price in decimal format")
    currency: str = Field(..., description="ISO 4217 currency code")
    timestamp: datetime = Field(..., description="When price was observed (UTC)")
    source: str = Field(..., description="Data source")
    is_stale: bool = Field(..., description="Whether price data is stale")


class BatchPriceItem(BaseModel):
    """Single price item in batch response."""

    ticker: str = Field(..., description="Stock ticker symbol")
    price: str = Field(..., description="Current price in decimal format")
    currency: str = Field(..., description="ISO 4217 currency code")
    timestamp: datetime = Field(..., description="When price was observed (UTC)")
    source: str = Field(..., description="Data source (alpha_vantage, cache, database)")
    is_stale: bool = Field(..., description="Whether price data is stale")


class BatchPriceResponse(BaseModel):
    """Response model for batch price query."""

    prices: dict[str, BatchPriceItem] = Field(
        ..., description="Mapping of ticker symbols to price data"
    )
    requested: int = Field(..., description="Number of tickers requested")
    returned: int = Field(..., description="Number of prices returned")


class SupportedTickersResponse(BaseModel):
    """Response model for supported tickers query."""

    tickers: list[str] = Field(..., description="List of supported ticker symbols")
    count: int = Field(..., description="Number of tickers")


class CheckHistoricalDataResponse(BaseModel):
    """Response model for historical data availability check."""

    available: bool = Field(..., description="Whether historical data exists")
    closest_date: datetime | None = Field(
        None, description="Closest available date if data exists"
    )


class FetchHistoricalDataRequest(BaseModel):
    """Request model for fetching historical data."""

    ticker: str = Field(..., min_length=1, max_length=5)
    start: datetime = Field(..., description="Start date (UTC)")
    end: datetime = Field(..., description="End date (UTC)")


class FetchHistoricalDataResponse(BaseModel):
    """Response model for historical data fetch."""

    ticker: str = Field(..., description="Stock ticker symbol")
    fetched: int = Field(..., description="Number of price points fetched")
    start: datetime = Field(..., description="Start of time range (UTC)")
    end: datetime = Field(..., description="End of time range (UTC)")


# Route Handlers


@router.get(
    "/batch",
    response_model=BatchPriceResponse,
    summary="Get current prices for multiple tickers",
    description="Fetches current prices for multiple tickers in a single batch request",
)
async def get_batch_prices(
    tickers: Annotated[
        str,
        Query(
            description=(
                "Comma-separated list of ticker symbols (e.g., 'AAPL,MSFT,GOOGL')"
            )
        ),
    ],
    market_data: MarketDataDep,
) -> BatchPriceResponse:
    """Get current prices for multiple tickers in batch.

    This endpoint optimizes price fetching by:
    - Checking cache for all tickers first
    - Only fetching uncached tickers from API
    - Returning partial results if some tickers fail

    Args:
        tickers: Comma-separated ticker symbols (e.g., "AAPL,MSFT,GOOGL")
        market_data: Market data port implementation (injected)

    Returns:
        BatchPriceResponse with prices for available tickers

    Example:
        GET /api/v1/prices/batch?tickers=AAPL,MSFT,GOOGL
    """
    # Parse comma-separated tickers
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    if not ticker_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ticker symbol is required",
        )

    # Convert to Ticker objects
    ticker_objs = [Ticker(t) for t in ticker_list]

    # Fetch batch prices
    prices_dict = await market_data.get_batch_prices(ticker_objs)

    # Convert to response format
    prices_response: dict[str, BatchPriceItem] = {}
    for ticker_obj, price_point in prices_dict.items():
        prices_response[ticker_obj.symbol] = BatchPriceItem(
            ticker=price_point.ticker.symbol,
            price=str(price_point.price.amount),
            currency=price_point.price.currency,
            timestamp=price_point.timestamp,
            source=price_point.source,
            is_stale=price_point.is_stale(max_age=timedelta(hours=1)),
        )

    return BatchPriceResponse(
        prices=prices_response,
        requested=len(ticker_list),
        returned=len(prices_response),
    )


@router.get(
    "/{ticker}",
    response_model=CurrentPriceResponse,
    summary="Get current price for a ticker",
    description="Fetches the most recent available price for a stock ticker",
)
async def get_current_price(
    ticker: str,
    market_data: MarketDataDep,
) -> CurrentPriceResponse:
    """Get current price for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        market_data: Market data port implementation (injected)

    Returns:
        CurrentPriceResponse with current price data

    Raises:
        HTTPException: 404 if ticker not found, 503 if market data unavailable
    """
    try:
        # Parse ticker
        ticker_obj = Ticker(ticker.upper())

        # Get current price
        price_point = await market_data.get_current_price(ticker_obj)

        # Convert to response model
        return CurrentPriceResponse(
            ticker=price_point.ticker.symbol,
            price=str(price_point.price.amount),
            currency=price_point.price.currency,
            timestamp=price_point.timestamp,
            source=price_point.source,
            is_stale=price_point.is_stale(max_age=timedelta(hours=1)),
        )

    except TickerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker not found: {ticker}",
        ) from e

    except MarketDataUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


@router.get(
    "/{ticker}/history",
    response_model=PriceHistoryResponse,
    summary="Get historical price data",
    description="Fetches historical price data for a ticker over a time range",
)
async def get_price_history(
    ticker: str,
    market_data: MarketDataDep,
    start: Annotated[
        str, Query(description="Start of time range (YYYY-MM-DD or ISO datetime)")
    ],
    end: Annotated[
        str, Query(description="End of time range (YYYY-MM-DD or ISO datetime)")
    ],
    interval: Annotated[
        str,
        Query(description="Price interval (1min, 5min, 1hour, 1day)"),
    ] = "1day",
) -> PriceHistoryResponse:
    """Get historical price data for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        market_data: Market data port implementation (injected)
        start: Start of time range (UTC)
        end: End of time range (UTC)
        interval: Price interval type (default: "1day")

    Returns:
        PriceHistoryResponse with list of price points

    Raises:
        HTTPException: 400 if invalid parameters, 404 if ticker not found,
                      503 if market data unavailable
    """
    try:
        # Parse ticker
        ticker_obj = Ticker(ticker.upper())

        # Parse dates - ensure timezone-aware datetimes (UTC)
        # Supports both "2026-01-12" (naive) and "2026-01-12T00:00:00Z" (aware) formats

        start_parsed = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_parsed = datetime.fromisoformat(end.replace("Z", "+00:00"))

        # If naive (no timezone), assume UTC
        start_dt = (
            start_parsed if start_parsed.tzinfo else start_parsed.replace(tzinfo=UTC)
        )
        end_dt = end_parsed if end_parsed.tzinfo else end_parsed.replace(tzinfo=UTC)

        # Bind ticker context for all logs in this request handler
        log = logger.bind(ticker=ticker, interval=interval)

        log.info(
            "Price history API request",
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
        )

        # Adjust end date to include full day if it's exactly midnight
        # When frontend sends "2026-01-17", it gets parsed as "2026-01-17T00:00:00"
        # but we want to include all data points on that day (up to 23:59:59.999999)
        adjusted_end = end_dt
        if end_dt.time() == end_dt.min.time():  # Check if time is 00:00:00
            from datetime import timedelta

            adjusted_end = end_dt + timedelta(days=1, microseconds=-1)

            log.debug(
                "Adjusted end date for midnight boundary",
                original_end=end_dt.isoformat(),
                adjusted_end=adjusted_end.isoformat(),
            )

        # Get price history
        history = await market_data.get_price_history(
            ticker_obj, start_dt, adjusted_end, interval
        )

        # Convert to response model
        prices = [
            PricePointResponse(
                ticker=p.ticker.symbol,
                price=str(p.price.amount),
                currency=p.price.currency,
                timestamp=p.timestamp,
                source=p.source,
                interval=p.interval,
            )
            for p in history
        ]

        # Log response metadata
        log.info(
            "Price history API response",
            count=len(prices),
            status="success",
        )

        # Warn if response is empty
        if len(prices) == 0:
            log.warning(
                "Price history returned empty",
                start=start_dt.isoformat(),
                end=adjusted_end.isoformat(),
            )

        return PriceHistoryResponse(
            ticker=ticker_obj.symbol,
            prices=prices,
            start=start_dt,
            end=adjusted_end,
            interval=interval,
            count=len(prices),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except TickerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker not found: {ticker}",
        ) from e

    except MarketDataUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


@router.get(
    "/",
    response_model=SupportedTickersResponse,
    summary="Get supported tickers",
    description="Returns list of all tickers we have price data for",
)
async def get_supported_tickers(
    market_data: MarketDataDep,
) -> SupportedTickersResponse:
    """Get list of supported tickers.

    Args:
        market_data: Market data port implementation (injected)

    Returns:
        SupportedTickersResponse with list of ticker symbols

    Raises:
        HTTPException: 503 if market data unavailable
    """
    try:
        tickers = await market_data.get_supported_tickers()

        return SupportedTickersResponse(
            tickers=[t.symbol for t in tickers],
            count=len(tickers),
        )

    except MarketDataUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


@router.get(
    "/{ticker}/check",
    response_model=CheckHistoricalDataResponse,
    summary="Check historical data availability",
    description="Check if historical price data exists for a ticker at a specific date",
)
async def check_historical_data(
    ticker: str,
    date: Annotated[datetime, Query(description="Date to check (UTC)")],
    market_data: MarketDataDep,
) -> CheckHistoricalDataResponse:
    """Check if historical data exists for a ticker on a specific date.

    This endpoint is used by the frontend to determine if historical price data
    is available before executing a backtest trade.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        date: Date to check for data availability (UTC)
        market_data: Market data port implementation (injected)

    Returns:
        CheckHistoricalDataResponse with availability status

    Raises:
        HTTPException: 400 if invalid ticker format, 503 if service unavailable
    """
    try:
        # Parse ticker
        ticker_obj = Ticker(ticker.upper())

        # Try to get price at the specified date
        price = await market_data.get_price_at(ticker_obj, date)

        return CheckHistoricalDataResponse(
            available=True,
            closest_date=price.timestamp,
        )

    except TickerNotFoundError:
        # Ticker not found - return available=False instead of error
        # This allows frontend to handle gracefully
        return CheckHistoricalDataResponse(
            available=False,
            closest_date=None,
        )

    except MarketDataUnavailableError:
        # No data available - return False instead of error
        return CheckHistoricalDataResponse(
            available=False,
            closest_date=None,
        )


@router.post(
    "/fetch-historical",
    response_model=FetchHistoricalDataResponse,
    summary="Fetch historical data",
    description="Fetch and store historical price data for a ticker",
)
async def fetch_historical_data(
    request: FetchHistoricalDataRequest,
    market_data: MarketDataDep,
) -> FetchHistoricalDataResponse:
    """Fetch historical data for a ticker and date range.

    This endpoint is called by the frontend when backtest mode detects missing
    historical data. It fetches data from Alpha Vantage and stores it in the
    database for future use.

    Args:
        request: Request with ticker and date range
        market_data: Market data port implementation (injected)

    Returns:
        FetchHistoricalDataResponse with fetch results

    Raises:
        HTTPException: 400 if invalid parameters, 404 if ticker not found,
                      503 if market data unavailable
    """
    try:
        # Parse ticker
        ticker_obj = Ticker(request.ticker.upper())

        # Fetch price history from API (will auto-store in database)
        history = await market_data.get_price_history(
            ticker_obj,
            start=request.start,
            end=request.end,
            interval="1day",
        )

        return FetchHistoricalDataResponse(
            ticker=ticker_obj.symbol,
            fetched=len(history),
            start=request.start,
            end=request.end,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except TickerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker not found: {request.ticker}",
        ) from e

    except MarketDataUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


@router.get(
    "/debug/cache/{ticker}",
    summary="Inspect price cache (Debug only)",
    description="Development endpoint to inspect cached price data for debugging",
    include_in_schema=True,
)
async def inspect_price_cache(
    ticker: str,
    market_data: MarketDataDep,
) -> dict[str, object]:
    """Inspect cached price data for debugging.

    **Development only** - shows what data exists in cache for a ticker.
    This endpoint helps diagnose data completeness issues by showing:
    - Total cached points for the ticker
    - Date range of cached data
    - List of all cached dates
    - Potential gaps in the data

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        market_data: Market data port implementation (injected)

    Returns:
        Dictionary with cache inspection data
    """
    try:
        from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
            AlphaVantageAdapter,
        )

        ticker_obj = Ticker(ticker.upper())

        # Get all data for this ticker (last 100 days)
        end = datetime.now()
        start = end - timedelta(days=100)

        # Check if we have access to price repository
        # (only available on AlphaVantageAdapter implementation)
        if not isinstance(market_data, AlphaVantageAdapter):
            return {
                "ticker": ticker,
                "status": "error",
                "message": "Debug endpoint only works with AlphaVantageAdapter",
            }

        if not market_data.price_repository:
            return {
                "ticker": ticker,
                "status": "error",
                "message": "Price repository not configured",
            }

        history = await market_data.price_repository.get_price_history(
            ticker_obj, start, end, "1day"
        )

        if not history:
            return {
                "ticker": ticker,
                "status": "no_data",
                "message": "No cached data found for this ticker",
            }

        # Extract dates and find gaps
        dates = [p.timestamp.date() for p in history]
        date_strings = [d.isoformat() for d in dates]

        # Simple gap detection: find dates more than 7 days apart
        # (allowing for weekends/holidays)
        gaps = []
        for i in range(len(dates) - 1):
            days_apart = (dates[i + 1] - dates[i]).days
            # More than a week gap (accounting for weekends/holidays)
            if days_apart > 7:
                gaps.append(
                    {
                        "after": dates[i].isoformat(),
                        "before": dates[i + 1].isoformat(),
                        "days_gap": days_apart,
                    }
                )

        return {
            "ticker": ticker,
            "status": "ok",
            "total_points": len(history),
            "date_range": {
                "start": history[0].timestamp.isoformat(),
                "end": history[-1].timestamp.isoformat(),
                "span_days": (dates[-1] - dates[0]).days,
            },
            "dates": date_strings,
            "gaps_detected": gaps,
            "sources": list({p.source for p in history}),
        }

    except Exception as e:
        logger.error(
            "Error inspecting price cache",
            ticker=ticker,
            error=str(e),
            exc_info=True,
        )
        return {
            "ticker": ticker,
            "status": "error",
            "message": f"Error inspecting cache: {str(e)}",
        }
