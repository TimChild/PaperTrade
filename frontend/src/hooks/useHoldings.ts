import { useQuery } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolio'

/**
 * Hook to fetch holdings for a portfolio
 */
export function useHoldings(portfolioId: string) {
  return useQuery({
    queryKey: ['holdings', portfolioId],
    queryFn: () => portfolioService.getHoldings(portfolioId),
    staleTime: 30_000, // 30 seconds for financial data
  })
}
