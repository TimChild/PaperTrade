/**
 * React Query hooks for strategies
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { strategiesApi } from '@/services/api/strategies'
import type { CreateStrategyRequest } from '@/services/api/types'

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategiesApi.list(),
    staleTime: 30_000,
  })
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: () => strategiesApi.getById(id),
    staleTime: 30_000,
    enabled: Boolean(id),
  })
}

export function useCreateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateStrategyRequest) => strategiesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => strategiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}
