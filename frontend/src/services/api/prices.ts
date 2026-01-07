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
 * Uses Promise.allSettled to handle individual failures gracefully
 */
export async function getBatchPrices(
  tickers: string[]
): Promise<Map<string, PricePoint>> {
  const results = await Promise.allSettled(
    tickers.map((ticker) => getCurrentPrice(ticker))
  )

  const priceMap = new Map<string, PricePoint>()
  results.forEach((result, index) => {
    if (result.status === 'fulfilled') {
      priceMap.set(tickers[index], result.value)
    }
  })

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
