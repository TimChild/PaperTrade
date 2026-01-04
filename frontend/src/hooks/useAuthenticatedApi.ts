/**
 * Hook to provide an authenticated API client with Clerk token injection
 */
import { useAuth } from '@clerk/clerk-react'
import { useEffect } from 'react'
import { apiClient } from '@/services/api/client'

/**
 * Hook that configures the global apiClient with Clerk authentication.
 * This should be called once at the app level to set up auth for all API calls.
 */
export function useAuthenticatedApi() {
  const { getToken } = useAuth()

  useEffect(() => {
    // Add request interceptor for auth token
    const requestInterceptor = apiClient.interceptors.request.use(
      async (config) => {
        try {
          const token = await getToken()
          if (token) {
            config.headers.Authorization = `Bearer ${token}`
          }
        } catch (error) {
          console.error('Failed to get auth token:', error)
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Cleanup: Remove interceptor when component unmounts
    return () => {
      apiClient.interceptors.request.eject(requestInterceptor)
    }
  }, [getToken])
}
