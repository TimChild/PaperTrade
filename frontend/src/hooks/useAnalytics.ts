/**
 * React Query hooks for analytics data
 */
import { useQuery } from '@tanstack/react-query'
import { analyticsApi, TimeRange } from '@/services/api/analytics'

/**
 * Hook to fetch portfolio performance data
 */
export function usePerformance(portfolioId: string, range: TimeRange = '1M') {
  return useQuery({
    queryKey: ['performance', portfolioId, range],
    queryFn: () => analyticsApi.getPerformance(portfolioId, range),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: Boolean(portfolioId),
  })
}

/**
 * Hook to fetch portfolio composition data
 */
export function useComposition(portfolioId: string) {
  return useQuery({
    queryKey: ['composition', portfolioId],
    queryFn: () => analyticsApi.getComposition(portfolioId),
    staleTime: 60 * 1000, // 1 minute (live prices)
    enabled: Boolean(portfolioId),
  })
}
