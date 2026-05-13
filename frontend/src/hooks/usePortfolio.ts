import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { portfoliosApi } from '@/services/api/portfolios'
import type {
  CreatePortfolioRequest,
  DepositRequest,
  WithdrawRequest,
  TradeRequest,
  BalanceResponse,
  PartialPricingFetchingBody,
} from '@/services/api/types'

/**
 * Phase J / Task #214 — maximum consecutive 503 "fetching" retries the
 * single-portfolio balance hook performs before surfacing a hard error.
 * Backend's ``retry_after_seconds`` default is 5; five retries ~ 25s
 * total which matches the spec's "stuck > 30s → bail out" budget.
 */
const MAX_PRICING_RETRIES = 5

function isPartialPricingFetchingBody(
  value: unknown
): value is PartialPricingFetchingBody {
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  if (obj.status !== 'fetching') return false
  if (!Array.isArray(obj.missing_tickers)) return false
  if (typeof obj.retry_after_seconds !== 'number') return false
  return true
}

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
 * Result returned by :func:`usePortfolioBalance` — extends a successful
 * balance with the Phase J / Task #214 ``pricingStatus`` discriminator
 * so consumers can render a loading skeleton instead of stale or
 * computed-against-partial-data numbers.
 */
export interface UsePortfolioBalanceResult {
  data: BalanceResponse | null
  isLoading: boolean
  isError: boolean
  error: unknown
  /**
   * - `ok` — every required price resolved; numeric fields on `data` are
   *   correct.
   * - `loading` — at least one held ticker's price could not be
   *   resolved. `data` may still carry `cash_balance` (always accurate)
   *   but the holdings/total/day-change fields are placeholders the UI
   *   must NOT render. The hook auto-retries up to
   *   :data:`MAX_PRICING_RETRIES` times.
   * - `unavailable` — retry budget exhausted; the user has been waiting
   *   ~30s+ with no resolution. UI should switch to a hard error block.
   */
  pricingStatus: 'ok' | 'loading' | 'unavailable'
  /** Tickers whose price could not be resolved (loading / unavailable). */
  missingTickers: string[]
  /** Retry budget remaining; useful for callers that want their own UX. */
  retriesRemaining: number
}

/**
 * Hook to fetch portfolio balance with Phase J / Task #214 pricing-state
 * awareness. Auto-retries the 503 ``fetching`` response shape using the
 * server-supplied ``retry_after_seconds`` cadence, up to
 * :data:`MAX_PRICING_RETRIES` consecutive attempts. After the retry
 * budget is exhausted the hook surfaces ``pricingStatus: "unavailable"``
 * with the list of stuck tickers so the UI can render the bail-out
 * affordance.
 *
 * Note: the balance response itself also carries ``pricing_status`` (the
 * list-endpoint convention), but for the single-portfolio endpoint the
 * server returns a 503 + ``Retry-After`` instead — those are caught here
 * and surfaced via ``pricingStatus`` so consumers have one API surface.
 */
export function usePortfolioBalance(
  portfolioId: string
): UsePortfolioBalanceResult {
  const query = useQuery<
    | { ok: true; balance: BalanceResponse }
    | {
        ok: false
        kind: 'loading' | 'unavailable'
        missingTickers: string[]
        retriesRemaining: number
        cashFallback: BalanceResponse | null
      },
    AxiosError
  >({
    queryKey: ['portfolio', portfolioId, 'balance'],
    queryFn: async () => {
      // Auto-retry the 503-fetching shape up to MAX_PRICING_RETRIES
      // times before bubbling. Outside that, any other error
      // propagates to react-query's normal error path.
      let attempt = 0
      let lastMissing: string[] = []
      while (true) {
        try {
          const balance = await portfoliosApi.getBalance(portfolioId)
          // Server also returns 200 with pricing_status="loading" on the
          // batch endpoint; this branch handles the singleton case
          // defensively in case the API ever returns 200 with that flag.
          if (balance.pricing_status === 'loading') {
            return {
              ok: false as const,
              kind: 'loading' as const,
              missingTickers: balance.missing_tickers ?? [],
              retriesRemaining: Math.max(0, MAX_PRICING_RETRIES - attempt),
              cashFallback: balance,
            }
          }
          return { ok: true as const, balance }
        } catch (err) {
          if (
            err instanceof AxiosError &&
            err.response?.status === 503 &&
            isPartialPricingFetchingBody(err.response.data)
          ) {
            const body = err.response.data
            lastMissing = body.missing_tickers
            if (attempt >= MAX_PRICING_RETRIES) {
              return {
                ok: false as const,
                kind: 'unavailable' as const,
                missingTickers: lastMissing,
                retriesRemaining: 0,
                cashFallback: null,
              }
            }
            await new Promise<void>((resolve) =>
              setTimeout(resolve, body.retry_after_seconds * 1000)
            )
            attempt += 1
            continue
          }
          throw err
        }
      }
    },
    enabled: Boolean(portfolioId),
    refetchInterval: 30_000, // Refetch every 30 seconds
    // The retry loop above handles 503-fetching; disable react-query's
    // own retry so we don't double up.
    retry: false,
  })

  if (query.data?.ok === true) {
    return {
      data: query.data.balance,
      isLoading: query.isLoading,
      isError: query.isError,
      error: query.error,
      pricingStatus: 'ok',
      missingTickers: [],
      retriesRemaining: MAX_PRICING_RETRIES,
    }
  }

  if (query.data?.ok === false) {
    return {
      data: query.data.cashFallback,
      isLoading: query.isLoading,
      isError: false,
      error: null,
      pricingStatus: query.data.kind,
      missingTickers: query.data.missingTickers,
      retriesRemaining: query.data.retriesRemaining,
    }
  }

  return {
    data: null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    pricingStatus: 'ok',
    missingTickers: [],
    retriesRemaining: MAX_PRICING_RETRIES,
  }
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

// Type for transaction list query data — mirrors PaginatedResponse<Transaction>
// with the `isNew` highlight flag we attach client-side.
type TransactionListQueryData = {
  items: Array<{ id: string; isNew?: boolean }>
  total: number
  limit: number
  offset: number
  has_more: boolean
}

/**
 * Hook to execute a trade (buy or sell)
 */
export function useExecuteTrade(portfolioId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: TradeRequest) =>
      portfoliosApi.executeTrade(portfolioId, data),
    onSuccess: (response) => {
      // Invalidate all related queries to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'balance'],
      })
      queryClient.invalidateQueries({
        queryKey: ['portfolio', portfolioId, 'holdings'],
      })

      // Mark the new transaction for highlighting
      const newTransactionId = response.transaction_id
      const transactionQueryKey = [
        'portfolio',
        portfolioId,
        'transactions',
        undefined,
      ]

      // Use refetchQueries to ensure data is available before marking
      queryClient
        .refetchQueries({
          queryKey: ['portfolio', portfolioId, 'transactions'],
        })
        .then(() => {
          // Update the transaction list to mark the new transaction
          queryClient.setQueryData<TransactionListQueryData>(
            transactionQueryKey,
            (oldData) => {
              if (!oldData) return oldData

              return {
                ...oldData,
                items: oldData.items.map((tx) =>
                  tx.id === newTransactionId ? { ...tx, isNew: true } : tx
                ),
              }
            }
          )

          // Remove the highlight after 3 seconds
          // Note: This runs in the mutation context, not component lifecycle,
          // so it doesn't need cleanup as the mutation is fire-and-forget
          setTimeout(() => {
            queryClient.setQueryData<TransactionListQueryData>(
              transactionQueryKey,
              (oldData) => {
                if (!oldData) return oldData

                return {
                  ...oldData,
                  items: oldData.items.map((tx) =>
                    tx.id === newTransactionId ? { ...tx, isNew: false } : tx
                  ),
                }
              }
            )
          }, 3000)
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
    onSuccess: (_, portfolioId) => {
      // Remove all queries related to the deleted portfolio to prevent errors
      queryClient.removeQueries({ queryKey: ['portfolio', portfolioId] })
      // Invalidate the portfolios list to refetch
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}
