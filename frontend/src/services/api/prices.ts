/**
 * Price API functions for fetching market data
 */
import { apiClient } from './client'
import type { PricePoint, PriceHistory } from '@/types/price'
import { parseApiError } from '@/utils/priceErrors'

/**
 * Fetch current price for a ticker
 */
export async function getCurrentPrice(ticker: string): Promise<PricePoint> {
  // Backend returns flat structure, need to transform to nested PricePoint
  const response = await apiClient.get<{
    ticker: string
    price: string
    currency: string
    timestamp: string
    source: string
    is_stale: boolean
  }>(`/prices/${ticker}`)

  const data = response.data

  // Transform flat API response to nested PricePoint structure
  return {
    ticker: { symbol: data.ticker },
    price: {
      amount: parseFloat(data.price),
      currency: data.currency,
    },
    timestamp: data.timestamp,
    source: data.source as 'alpha_vantage' | 'cache' | 'database',
    interval: 'real-time', // Current price endpoint always returns real-time
  }
}

/**
 * Check if historical price data exists for a ticker at a specific date
 * Used by backtest mode to verify data availability
 */
export async function checkHistoricalPrice(
  ticker: string,
  date: string
): Promise<{ available: boolean; closest_date?: string }> {
  const response = await apiClient.get<{
    available: boolean
    closest_date: string | null
  }>(`/prices/${ticker}/check`, {
    params: { date },
  })

  return {
    available: response.data.available,
    closest_date: response.data.closest_date || undefined,
  }
}

/**
 * Get historical price for a ticker at a specific date
 * Returns the closest available price if exact date not available
 */
export async function getHistoricalPrice(
  ticker: string,
  date: string
): Promise<PricePoint> {
  // Use the /history endpoint with a 1-day range around the target date
  const response = await apiClient.get<{
    ticker: string
    prices: Array<{
      ticker: string
      price: string
      currency: string
      timestamp: string
      source: string
      interval: string
    }>
    start: string
    end: string
    interval: string
    count: number
  }>(`/prices/${ticker}/history`, {
    params: {
      start: date,
      end: date,
      interval: '1day',
    },
  })

  if (!response.data.prices || response.data.prices.length === 0) {
    throw new Error(`No price data available for ${ticker} at ${date}`)
  }

  // Return first (and should be only) price point
  const priceData = response.data.prices[0]
  return {
    ticker: { symbol: priceData.ticker },
    price: {
      amount: parseFloat(priceData.price),
      currency: priceData.currency,
    },
    timestamp: priceData.timestamp,
    source: priceData.source as 'alpha_vantage' | 'cache' | 'database',
    interval: priceData.interval as
      | '1day'
      | 'real-time'
      | '1hour'
      | '5min'
      | '1min',
  }
}


/**
 * Batch fetch prices for multiple tickers
 * Uses the /prices/batch endpoint for efficient single-request fetching
 */
export async function getBatchPrices(
  tickers: string[]
): Promise<Map<string, PricePoint>> {
  // Return empty map if no tickers provided
  if (tickers.length === 0) {
    return new Map()
  }

  // Call batch endpoint with comma-separated tickers
  const response = await apiClient.get<{
    prices: Record<
      string,
      {
        ticker: string
        price: string
        currency: string
        timestamp: string
        source: string
        is_stale: boolean
      }
    >
    requested: number
    returned: number
  }>('/prices/batch', {
    params: { tickers: tickers.join(',') },
  })

  // Convert backend response format to Map<string, PricePoint>
  const priceMap = new Map<string, PricePoint>()
  for (const [ticker, priceData] of Object.entries(response.data.prices)) {
    // Validate source value or default to 'database'
    const validSources: Array<'alpha_vantage' | 'cache' | 'database'> = [
      'alpha_vantage',
      'cache',
      'database',
    ]
    const source = validSources.includes(
      priceData.source as 'alpha_vantage' | 'cache' | 'database'
    )
      ? (priceData.source as 'alpha_vantage' | 'cache' | 'database')
      : 'database'

    priceMap.set(ticker, {
      ticker: { symbol: priceData.ticker },
      price: {
        amount: parseFloat(priceData.price),
        currency: priceData.currency,
      },
      timestamp: priceData.timestamp,
      source,
      interval: 'real-time',
    })
  }

  return priceMap
}

/**
 * Fetch price history for a ticker within a date range
 * Backend returns prices as strings, we parse them to numbers
 */
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    // Backend returns prices as strings, need to parse to numbers
    const response = await apiClient.get<{
      ticker: string
      prices: Array<{
        ticker: string
        price: string // Backend sends string
        currency: string
        timestamp: string
        source: string
        interval: string
      }>
    }>(`/prices/${ticker}/history`, {
      params: { start: startDate, end: endDate },
    })

    // Convert backend response to PriceHistory with number prices
    const priceHistory: PriceHistory = {
      ticker: response.data.ticker,
      prices: response.data.prices.map((point) => ({
        ticker: { symbol: point.ticker },
        price: {
          amount: parseFloat(point.price), // Parse string to number
          currency: point.currency,
        },
        timestamp: point.timestamp,
        source: point.source as 'alpha_vantage' | 'cache' | 'database',
        interval: point.interval as
          | '1day'
          | 'real-time'
          | '1hour'
          | '5min'
          | '1min',
      })),
      source: response.data.prices[0]?.source || 'unknown',
      cached: response.data.prices[0]?.source === 'cache',
    }

    return priceHistory
  } catch (error) {
    // Parse error into ApiError type
    const apiError = parseApiError(error, ticker)

    // In development mode, show mock data with warning banner
    if (import.meta.env.DEV) {
      console.warn('[DEV] API error, using mock data:', apiError.message)
      return {
        ...generateMockPriceHistory(ticker, startDate, endDate),
        error: apiError, // Include error in response
      }
    }

    // In production, throw structured error for component to handle
    throw apiError
  }
}

/**
 * Generate mock price history data for development
 * This will be removed once the backend API is available
 */
function generateMockPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): PriceHistory {
  const start = new Date(startDate)
  const end = new Date(endDate)
  const days = Math.ceil(
    (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)
  )

  const prices: PricePoint[] = []
  let basePrice = 150 + Math.random() * 100 // Random starting price between 150-250

  for (let i = 0; i <= days; i++) {
    const date = new Date(start)
    date.setDate(start.getDate() + i)

    // Random walk with some volatility
    const change = (Math.random() - 0.5) * 5
    basePrice = Math.max(50, basePrice + change) // Don't go below 50

    prices.push({
      ticker: { symbol: ticker },
      price: {
        amount: Number(basePrice.toFixed(2)),
        currency: 'USD',
      },
      timestamp: date.toISOString(),
      source: 'cache',
      interval: '1day',
    })
  }

  return {
    ticker,
    prices,
    source: 'mock',
    cached: false,
  }
}

export const pricesApi = {
  getCurrentPrice,
  getBatchPrices,
  getPriceHistory,
}
