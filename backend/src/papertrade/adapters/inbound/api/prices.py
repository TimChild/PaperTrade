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


class SupportedTickersResponse(BaseModel):
    """Response model for supported tickers query."""

    tickers: list[str] = Field(..., description="List of supported ticker symbols")
    count: int = Field(..., description="Number of tickers")


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
