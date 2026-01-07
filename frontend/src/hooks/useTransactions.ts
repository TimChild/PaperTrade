import { useQuery } from '@tanstack/react-query'
import {
  transactionsApi,
  type ListTransactionsParams,
} from '@/services/api/transactions'

/**
 * Hook to fetch transactions for a portfolio with optional pagination
 */
export function useTransactions(
  portfolioId: string,
  params?: ListTransactionsParams
) {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'transactions', params],
    queryFn: () => transactionsApi.list(portfolioId, params),
    staleTime: 30_000,
    enabled: Boolean(portfolioId),
  })
}
