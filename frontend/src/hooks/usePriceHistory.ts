/**
 * React Query hook for fetching price history data
 */
import { useQuery } from '@tanstack/react-query'
import { getPriceHistory } from '@/services/api/prices'
import type { TimeRange } from '@/types/price'

/**
 * Calculate date range based on time range selector
 */
function getDateRange(range: TimeRange): { start: string; end: string } {
  const end = new Date()
  const start = new Date()

  switch (range) {
    case '1D':
      start.setDate(end.getDate() - 1)
      break
    case '1W':
      start.setDate(end.getDate() - 7)
      break
    case '1M':
      start.setMonth(end.getMonth() - 1)
      break
    case '3M':
      start.setMonth(end.getMonth() - 3)
      break
    case '1Y':
      start.setFullYear(end.getFullYear() - 1)
      break
    case 'ALL':
      // For "ALL", go back 5 years
      start.setFullYear(end.getFullYear() - 5)
      break
  }

  return {
    start: start.toISOString().split('T')[0], // YYYY-MM-DD format
    end: end.toISOString().split('T')[0],
  }
}

/**
 * Hook to fetch price history for a ticker over a specified time range
 * Uses TanStack Query for caching and automatic refetching
 */
export function usePriceHistory(ticker: string, range: TimeRange) {
  const { start, end } = getDateRange(range)

  return useQuery({
    queryKey: ['priceHistory', ticker, range],
    queryFn: () => getPriceHistory(ticker, start, end),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: Boolean(ticker), // Only run if we have a ticker
    retry: 1, // Retry once if failed
  })
}
