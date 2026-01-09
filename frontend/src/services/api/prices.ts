/**
 * Price API functions for fetching market data
 */
import { apiClient } from './client'
import type { PricePoint, PriceHistory } from '@/types/price'

/**
 * Fetch current price for a ticker
 */
export async function getCurrentPrice(ticker: string): Promise<PricePoint> {
  const response = await apiClient.get<PricePoint>(`/prices/${ticker}`)
  return response.data
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
    priceMap.set(ticker, {
      ticker: { symbol: priceData.ticker },
      price: {
        amount: parseFloat(priceData.price),
        currency: priceData.currency,
      },
      timestamp: priceData.timestamp,
      source: priceData.source as 'alpha_vantage' | 'cache' | 'database',
      interval: 'real-time',
    })
  }

  return priceMap
}

/**
 * Fetch price history for a ticker within a date range
 * This will call the backend API endpoint once Task 031 is completed
 * For now, returns mock data to enable frontend development
 */
export async function getPriceHistory(
  ticker: string,
  startDate: string,
  endDate: string
): Promise<PriceHistory> {
  try {
    const response = await apiClient.get<PriceHistory>(
      `/prices/${ticker}/history`,
      {
        params: { start: startDate, end: endDate },
      }
    )
    return response.data
  } catch {
    // Backend endpoint doesn't exist yet (Task 031 pending)
    // Return mock data for development
    console.warn(
      `Price history API not available, using mock data for ${ticker}`
    )
    return generateMockPriceHistory(ticker, startDate, endDate)
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
