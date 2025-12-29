/**
 * Price API functions for fetching market data
 */
import { apiClient } from './client'
import type { PricePoint } from '@/types/price'

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

export const pricesApi = {
  getCurrentPrice,
  getBatchPrices,
}
