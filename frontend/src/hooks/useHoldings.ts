import { useQuery } from '@tanstack/react-query'
import { portfoliosApi } from '@/services/api'

/**
 * Hook to fetch holdings for a portfolio
 */
export function useHoldings(portfolioId: string) {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'holdings'],
    queryFn: () => portfoliosApi.getHoldings(portfolioId),
    enabled: Boolean(portfolioId),
    staleTime: 30_000, // 30 seconds for financial data
    refetchInterval: 30_000, // Refetch every 30 seconds
  })
}
