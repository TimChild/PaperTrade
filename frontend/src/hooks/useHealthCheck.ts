import { useQuery } from '@tanstack/react-query'
import { healthService } from '@/services/health'

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthService.check,
    refetchInterval: 30000, // Refresh every 30 seconds
    // Health checks are allowed more retries than the global default to be
    // more tolerant of transient connectivity or startup issues.
    retry: 3,
  })
}
