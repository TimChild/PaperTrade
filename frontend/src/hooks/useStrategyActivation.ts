/**
 * React Query hooks for strategy activations (Phase C1.4).
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'
import {
  strategyActivationsApi,
  type ListActivationsParams,
} from '@/services/api/strategyActivations'
import type {
  ActivateStrategyRequest,
  PaginatedResponse,
  RunNowResponse,
  StrategyActivationResponse,
} from '@/services/api/types'

/** Stable query keys used across the activation feature. */
export const activationQueryKeys = {
  all: ['activations'] as const,
  list: (params?: ListActivationsParams) =>
    ['activations', 'list', params] as const,
  byStrategy: (strategyId: string) =>
    ['activations', 'by-strategy', strategyId] as const,
}

/**
 * Fetch the activation linked to a strategy.
 *
 * Returns `null` if no activation exists for the strategy (backend 404 is
 * mapped to a cleanly-typed empty result by the API client).
 */
export function useStrategyActivation(
  strategyId: string
): UseQueryResult<StrategyActivationResponse | null> {
  return useQuery<StrategyActivationResponse | null>({
    queryKey: activationQueryKeys.byStrategy(strategyId),
    queryFn: () => strategyActivationsApi.getByStrategy(strategyId),
    staleTime: 30_000,
    enabled: Boolean(strategyId),
  })
}

/**
 * Paginated list of the current user's activations.
 */
export function useActivations(
  params?: ListActivationsParams
): UseQueryResult<PaginatedResponse<StrategyActivationResponse>> {
  return useQuery<PaginatedResponse<StrategyActivationResponse>>({
    queryKey: activationQueryKeys.list(params),
    queryFn: () => strategyActivationsApi.list(params),
    staleTime: 30_000,
  })
}

/**
 * Single activation by id, looked up via the list endpoint.
 *
 * The backend currently exposes activations via the user-scoped list and
 * the `/strategies/{id}/activation` shortcut. There's no
 * `GET /activations/{id}` endpoint yet (it'd be a sensible add but is out
 * of scope for G-1), so this hook fetches the full list and selects the
 * matching id client-side. Returns `null` when the id isn't present in the
 * page — typically a 404-equivalent state (deleted / never existed / not
 * owned). Disabled when `activationId` is falsy.
 *
 * Server-side pagination defaults to 20; for users with more than 20
 * activations we'd need a server-side lookup. Acceptable trade-off for
 * G-1; a follow-up should add `GET /activations/{id}`.
 */
export function useActivationById(
  activationId: string
): UseQueryResult<StrategyActivationResponse | null> {
  return useQuery<StrategyActivationResponse | null>({
    queryKey: ['activations', 'by-id', activationId] as const,
    queryFn: async () => {
      // Request a generous page so a user with a dozen activations still
      // finds the right one. 100 is the backend's MAX_PAGE_LIMIT.
      const page = await strategyActivationsApi.list({ limit: 100 })
      return page.items.find((a) => a.id === activationId) ?? null
    },
    staleTime: 30_000,
    enabled: Boolean(activationId),
  })
}

/**
 * Variables passed to the activate-strategy mutation.
 *
 * Combined into a single object so `mutate({...})` mirrors the call shape of
 * the API client (`activate(strategyId, body)`).
 */
export interface ActivateStrategyVariables {
  strategyId: string
  body: ActivateStrategyRequest
}

/**
 * Activate a strategy. Invalidates list + by-strategy queries on success so
 * the new activation surfaces in any rendered list/badge without a refresh.
 */
export function useActivateStrategy(): UseMutationResult<
  StrategyActivationResponse,
  Error,
  ActivateStrategyVariables
> {
  const queryClient = useQueryClient()
  return useMutation<
    StrategyActivationResponse,
    Error,
    ActivateStrategyVariables
  >({
    mutationFn: ({ strategyId, body }) =>
      strategyActivationsApi.activate(strategyId, body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: activationQueryKeys.all })
      void queryClient.invalidateQueries({
        queryKey: activationQueryKeys.byStrategy(variables.strategyId),
      })
    },
  })
}

/**
 * Variables passed to the deactivate mutation.
 */
export interface DeactivateActivationVariables {
  activationId: string
  /** Optional human-readable reason captured on `deactivation_reason`. */
  reason?: string
  /** Optional — the strategy this activation belongs to, used to invalidate the by-strategy cache key. */
  strategyId?: string
}

/**
 * Deactivate (pause) an activation. Invalidates the activations list and,
 * when provided, the by-strategy cache key.
 */
export function useDeactivateActivation(): UseMutationResult<
  StrategyActivationResponse,
  Error,
  DeactivateActivationVariables
> {
  const queryClient = useQueryClient()
  return useMutation<
    StrategyActivationResponse,
    Error,
    DeactivateActivationVariables
  >({
    mutationFn: ({ activationId, reason }) =>
      strategyActivationsApi.deactivate(activationId, reason),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: activationQueryKeys.all })
      if (variables.strategyId) {
        void queryClient.invalidateQueries({
          queryKey: activationQueryKeys.byStrategy(variables.strategyId),
        })
      }
    },
  })
}

/**
 * Variables passed to the run-now mutation.
 */
export interface RunActivationNowVariables {
  activationId: string
  /** Optional — the strategy this activation belongs to, used to invalidate the by-strategy cache key. */
  strategyId?: string
}

/**
 * Trigger immediate execution of an activation. Invalidates the activations
 * list (and by-strategy when known) so the post-run state — including any
 * status flip to ERROR — surfaces immediately.
 */
export function useRunActivationNow(): UseMutationResult<
  RunNowResponse,
  Error,
  RunActivationNowVariables
> {
  const queryClient = useQueryClient()
  return useMutation<RunNowResponse, Error, RunActivationNowVariables>({
    mutationFn: ({ activationId }) =>
      strategyActivationsApi.runNow(activationId),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: activationQueryKeys.all })
      if (variables.strategyId) {
        void queryClient.invalidateQueries({
          queryKey: activationQueryKeys.byStrategy(variables.strategyId),
        })
      }
    },
  })
}
