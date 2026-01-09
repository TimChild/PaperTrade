"""Price API routes.

Provides REST endpoints for price data operations:
- Get current price for a ticker
- Get historical price data for a ticker
- Get supported tickers
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from papertrade.adapters.inbound.api.dependencies import MarketDataDep
from papertrade.application.exceptions import (
    MarketDataUnavailableError,
    TickerNotFoundError,
)
from papertrade.domain.value_objects.ticker import Ticker

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
    "/{ticker}/history",
    response_model=PriceHistoryResponse,
    summary="Get historical price data",
    description="Fetches historical price data for a ticker over a time range",
)
async def get_price_history(
    ticker: str,
    market_data: MarketDataDep,
    start: Annotated[datetime, Query(description="Start of time range (UTC)")],
    end: Annotated[datetime, Query(description="End of time range (UTC)")],
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

        # Get price history
        history = await market_data.get_price_history(ticker_obj, start, end, interval)

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

        return PriceHistoryResponse(
            ticker=ticker_obj.symbol,
            prices=prices,
            start=start,
            end=end,
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
