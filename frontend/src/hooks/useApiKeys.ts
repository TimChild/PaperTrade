/**
 * React Query hooks for API key management.
 *
 * Mint flow note: `useCreateApiKey` returns the response containing `raw_key`
 * via the mutation's `data`. Consumers must capture and display it
 * immediately — subsequent renders / list fetches will not include it.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi } from '@/services/api/apiKeys'
import type { CreateApiKeyRequest } from '@/services/api/types'

const apiKeysQueryKey = ['api-keys'] as const

export function useApiKeys() {
  return useQuery({
    queryKey: apiKeysQueryKey,
    queryFn: () => apiKeysApi.list(),
    staleTime: 30_000,
  })
}

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateApiKeyRequest) => apiKeysApi.create(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: apiKeysQueryKey })
    },
  })
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiKeysApi.revoke(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: apiKeysQueryKey })
    },
  })
}
