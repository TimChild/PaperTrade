import { useQuery } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolio'

/**
 * Hook to fetch all portfolios
 */
export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfolioService.getAll(),
    staleTime: 30_000, // 30 seconds
  })
}

/**
 * Hook to fetch a single portfolio by ID
 */
export function usePortfolio(portfolioId: string) {
  return useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: () => portfolioService.getById(portfolioId),
    staleTime: 30_000,
    enabled: Boolean(portfolioId),
  })
}
