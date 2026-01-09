import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portfoliosApi } from '@/services/api/portfolios'
import type {
  CreatePortfolioRequest,
  DepositRequest,
  WithdrawRequest,
  TradeRequest,
} from '@/services/api/types'

/**
 * Hook to fetch all portfolios
 */
export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfoliosApi.list(),
    staleTime: 30_000, // 30 seconds
  })
}

/**
 * Hook to fetch a single portfolio by ID
 */
export function usePortfolio(portfolioId: string) {
  return useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: () => portfoliosApi.getById(portfolioId),
    staleTime: 30_000,
    enabled: Boolean(portfolioId),
  })
}

/**
 * Hook to fetch portfolio cash balance
 */
export function usePortfolioBalance(portfolioId: string) {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'balance'],
    queryFn: () => portfoliosApi.getBalance(portfolioId),
    enabled: Boolean(portfolioId),
    refetchInterval: 30_000, // Refetch every 30 seconds
  })
}

/**
 * Hook to create a new portfolio
 */
export function useCreatePortfolio() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreatePortfolioRequest) => portfoliosApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

/**
 * Hook to deposit cash into a portfolio
 */
export function useDeposit(portfolioId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DepositRequest) =>
      portfoliosApi.deposit(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'balance'],
      })
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'transactions'],
      })
    },
  })
}

/**
 * Hook to withdraw cash from a portfolio
 */
export function useWithdraw(portfolioId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: WithdrawRequest) =>
      portfoliosApi.withdraw(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'balance'],
      })
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'transactions'],
      })
    },
  })
}

/**
 * Hook to execute a trade (buy or sell)
 */
export function useExecuteTrade(portfolioId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: TradeRequest) =>
      portfoliosApi.executeTrade(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'balance'],
      })
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'holdings'],
      })
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'transactions'],
      })
    },
  })
}

/**
 * Hook to delete a portfolio
 */
export function useDeletePortfolio() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (portfolioId: string) => portfoliosApi.delete(portfolioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}
