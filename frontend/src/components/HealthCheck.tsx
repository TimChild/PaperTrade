import { useHealthCheck } from '@/hooks/useHealthCheck'

export function HealthCheck() {
  const { data, isLoading, isError, error } = useHealthCheck()

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-300 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 animate-pulse rounded-full bg-yellow-500"></div>
          <span className="text-sm text-gray-700 dark:text-gray-300">
            Checking backend connection...
          </span>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-700 dark:bg-red-900/20">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-red-500"></div>
          <span className="text-sm text-red-700 dark:text-red-400">
            Backend unavailable:{' '}
            {error instanceof Error ? error.message : 'Unknown error'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-green-300 bg-green-50 p-4 dark:border-green-700 dark:bg-green-900/20">
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 rounded-full bg-green-500"></div>
        <span className="text-sm text-green-700 dark:text-green-400">
          Backend connected: {data?.status || 'OK'}
        </span>
      </div>
    </div>
  )
}
