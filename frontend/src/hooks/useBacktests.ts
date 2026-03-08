/**
 * React Query hooks for backtests
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { backtestsApi } from '@/services/api/backtests'
import type { RunBacktestRequest } from '@/services/api/types'

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.list(),
    staleTime: 30_000,
  })
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: () => backtestsApi.getById(id),
    staleTime: 30_000,
    enabled: Boolean(id),
  })
}

export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: RunBacktestRequest) => backtestsApi.run(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => backtestsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}
