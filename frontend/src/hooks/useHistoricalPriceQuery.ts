/**
 * React Query hook for fetching historical price data
 * Used by TradeForm when backtest mode is enabled
 */
import { useQuery } from '@tanstack/react-query'
import { getHistoricalPrice } from '@/services/api/prices'
import type { AxiosError } from 'axios'

/**
 * Hook to fetch historical price for a ticker at a specific date
 * Used when backtest mode is enabled in TradeForm
 */
export function useHistoricalPriceQuery(ticker: string, date: string) {
  return useQuery({
    queryKey: ['price-historical', ticker, date],
    queryFn: () => getHistoricalPrice(ticker, date),
    staleTime: 60 * 60 * 1000, // Historical data is stable - cache for 1 hour
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours
    refetchInterval: false, // Never auto-refetch historical data
    retry: (failureCount, error) => {
      const axiosError = error as AxiosError
      // Don't retry on not found (404) or service unavailable (503)
      if (
        axiosError?.response?.status === 404 ||
        axiosError?.response?.status === 503
      ) {
        return false
      }
      return failureCount < 2
    },
    enabled: Boolean(ticker) && Boolean(date),
  })
}
