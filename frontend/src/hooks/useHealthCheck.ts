import { useQuery } from '@tanstack/react-query'
import { healthService } from '@/services/health'

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthService.check,
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 3,
  })
}
