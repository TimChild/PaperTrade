import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolio'
import type { TradeRequest } from '@/types/portfolio'

/**
 * Hook to fetch transactions for a portfolio
 */
export function useTransactions(portfolioId: string) {
  return useQuery({
    queryKey: ['transactions', portfolioId],
    queryFn: () => portfolioService.getTransactions(portfolioId),
    staleTime: 30_000,
    enabled: !!portfolioId,
  })
}

/**
 * Hook to execute a trade
 */
export function useExecuteTrade() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: TradeRequest) => portfolioService.executeTrade(request),
    onSuccess: (_, variables) => {
      // Invalidate related queries to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['portfolio', variables.portfolioId],
      })
      queryClient.invalidateQueries({
        queryKey: ['holdings', variables.portfolioId],
      })
      queryClient.invalidateQueries({
        queryKey: ['transactions', variables.portfolioId],
      })
    },
  })
}
