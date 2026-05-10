/**
 * React Query hooks for triggers (Phase G-1).
 *
 * The list hook scopes by activation id so the trigger configuration section
 * lives on the activation detail surface. The fire-log hook is paginated and
 * keyed by trigger id; it's used both inline (in the per-trigger actions row)
 * and on the dedicated fire-log page.
 *
 * Mutations invalidate the affected list / by-id caches so any rendered
 * detail / list view re-fetches once the request settles.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'
import { triggersApi } from '@/services/api/triggers'
import type {
  CreateTriggerRequest,
  ListTriggerParams,
  PaginatedResponse,
  TriggerFireResponse,
  TriggerResponse,
  UpdateTriggerRequest,
} from '@/services/api/types'

/** Stable query keys used across the trigger feature. */
export const triggerQueryKeys = {
  all: ['triggers'] as const,
  listByActivation: (activationId: string, params?: ListTriggerParams) =>
    ['triggers', 'by-activation', activationId, params] as const,
  byId: (triggerId: string) => ['triggers', 'by-id', triggerId] as const,
  fires: (triggerId: string, params?: ListTriggerParams) =>
    ['triggers', 'fires', triggerId, params] as const,
}

/**
 * Paginated list of triggers attached to an activation. Disabled when
 * `activationId` is falsy so the hook can be used on detail pages where the
 * id may not be available until after a route param parse.
 */
export function useTriggers(
  activationId: string,
  params?: ListTriggerParams
): UseQueryResult<PaginatedResponse<TriggerResponse>> {
  return useQuery<PaginatedResponse<TriggerResponse>>({
    queryKey: triggerQueryKeys.listByActivation(activationId, params),
    queryFn: () => triggersApi.listForActivation(activationId, params),
    staleTime: 30_000,
    enabled: Boolean(activationId),
  })
}

/**
 * Single trigger by id. Returns the full trigger; the renderer narrows on
 * `condition_type` to surface the right param shape.
 */
export function useTrigger(triggerId: string): UseQueryResult<TriggerResponse> {
  return useQuery<TriggerResponse>({
    queryKey: triggerQueryKeys.byId(triggerId),
    queryFn: () => triggersApi.getById(triggerId),
    staleTime: 30_000,
    enabled: Boolean(triggerId),
  })
}

/**
 * Paginated trigger fire log. Newest-first per the backend contract. The
 * `condition_evaluation_data` blob is per-condition; renderers infer the
 * shape from the parent trigger's `condition_type`.
 */
export function useTriggerFires(
  triggerId: string,
  params?: ListTriggerParams
): UseQueryResult<PaginatedResponse<TriggerFireResponse>> {
  return useQuery<PaginatedResponse<TriggerFireResponse>>({
    queryKey: triggerQueryKeys.fires(triggerId, params),
    queryFn: () => triggersApi.listFires(triggerId, params),
    staleTime: 30_000,
    enabled: Boolean(triggerId),
  })
}

/** Mutation variables for `useCreateTrigger`. */
export interface CreateTriggerVariables {
  activationId: string
  body: CreateTriggerRequest
}

/**
 * Attach a new trigger to an activation. Invalidates the activation's
 * trigger list cache so the new row surfaces immediately.
 */
export function useCreateTrigger(): UseMutationResult<
  TriggerResponse,
  Error,
  CreateTriggerVariables
> {
  const queryClient = useQueryClient()
  return useMutation<TriggerResponse, Error, CreateTriggerVariables>({
    mutationFn: ({ activationId, body }) =>
      triggersApi.create(activationId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: triggerQueryKeys.all })
    },
  })
}

/** Mutation variables for `useUpdateTrigger`. */
export interface UpdateTriggerVariables {
  triggerId: string
  body: UpdateTriggerRequest
}

/**
 * PATCH a trigger. Invalidates the affected list + by-id cache so consumers
 * re-fetch. Caller-side handlers (pause/resume/edit dialogs) attach onSuccess
 * toasts on top of this.
 */
export function useUpdateTrigger(): UseMutationResult<
  TriggerResponse,
  Error,
  UpdateTriggerVariables
> {
  const queryClient = useQueryClient()
  return useMutation<TriggerResponse, Error, UpdateTriggerVariables>({
    mutationFn: ({ triggerId, body }) => triggersApi.update(triggerId, body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: triggerQueryKeys.all })
      void queryClient.invalidateQueries({
        queryKey: triggerQueryKeys.byId(variables.triggerId),
      })
    },
  })
}

/**
 * Soft-delete a trigger (transitions to EXPIRED). Invalidates the activation
 * trigger list and the per-trigger cache. Past fires are preserved so the
 * fire-log endpoint still renders history.
 */
export function useDeleteTrigger(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (triggerId: string) => triggersApi.delete(triggerId),
    onSuccess: (_data, triggerId) => {
      void queryClient.invalidateQueries({ queryKey: triggerQueryKeys.all })
      void queryClient.invalidateQueries({
        queryKey: triggerQueryKeys.byId(triggerId),
      })
    },
  })
}
