/**
 * React Query hooks for fetching price data
 */
import { useQuery } from '@tanstack/react-query'
import { getCurrentPrice, getBatchPrices } from '@/services/api/prices'
import type { PricePoint } from '@/types/price'

/**
 * Hook to fetch current price for a single ticker
 * Uses TanStack Query for caching and automatic refetching
 */
export function usePriceQuery(ticker: string) {
  return useQuery({
    queryKey: ['price', ticker],
    queryFn: () => getCurrentPrice(ticker),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refetch every 5 minutes
    retry: 3,
    enabled: Boolean(ticker),
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
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000, // Auto-refetch every 5 minutes
    enabled: tickers.length > 0, // Only run if we have tickers
    retry: 3,
  })
}

/**
 * Utility hook for price staleness calculation
 * Returns a human-readable string indicating how old the price is
 */
export function usePriceStaleness(pricePoint: PricePoint | undefined): string | null {
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
