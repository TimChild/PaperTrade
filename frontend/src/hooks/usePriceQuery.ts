/**
 * React Query hooks for fetching price data
 */
import { useQuery } from '@tanstack/react-query'
import { getCurrentPrice, getBatchPrices } from '@/services/api/prices'
import type { PricePoint } from '@/types/price'
import type { AxiosError } from 'axios'

/**
 * Hook to fetch current price for a single ticker
 * Uses TanStack Query for caching and automatic refetching
 */
export function usePriceQuery(ticker: string) {
  return useQuery({
    queryKey: ['price', ticker],
    queryFn: () => getCurrentPrice(ticker),
    staleTime: 60 * 1000, // Consider data fresh for 1 minute
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
    refetchInterval: false, // Don't auto-refetch to avoid rate limiting
    retry: (failureCount, error) => {
      const axiosError = error as AxiosError
      // Don't retry on rate limit (503) or not found (404)
      if (
        axiosError?.response?.status === 503 ||
        axiosError?.response?.status === 404
      ) {
        return false
      }
      return failureCount < 2
    },
    enabled: Boolean(ticker),
    // Keep previous data on error to show last known price
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook to fetch prices for multiple tickers
 * Returns a Map<ticker, PricePoint> for easy lookup
 */
export function useBatchPricesQuery(tickers: string[]) {
  return useQuery({
    queryKey: ['prices', ...tickers.sort()],
    queryFn: () => getBatchPrices(tickers),
    staleTime: 60 * 1000, // Consider data fresh for 1 minute
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
    refetchInterval: false, // Don't auto-refetch to avoid rate limiting
    enabled: tickers.length > 0, // Only run if we have tickers
    retry: (failureCount, error) => {
      const axiosError = error as AxiosError
      // Don't retry on rate limit (503)
      if (axiosError?.response?.status === 503) {
        return false
      }
      return failureCount < 2
    },
    // Keep previous data on error to show last known prices
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Utility hook for price staleness calculation
 * Returns a human-readable string indicating how old the price is
 */
export function usePriceStaleness(
  pricePoint: PricePoint | undefined
): string | null {
  if (!pricePoint) return null

  const now = new Date()
  const priceTime = new Date(pricePoint.timestamp)
  const diffMs = now.getTime() - priceTime.getTime()
  const diffMinutes = Math.floor(diffMs / 60000)

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60)
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
}
