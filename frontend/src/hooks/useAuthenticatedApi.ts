/**
 * Hook to provide an authenticated API client with Clerk token injection
 */
import { useAuth } from '@clerk/clerk-react'
import { useEffect } from 'react'
import { apiClient } from '@/services/api/client'

// Check if running in E2E test mode
const isE2ETestMode = () => {
  return typeof window !== 'undefined' && window.location.search.includes('e2e-test=true')
}

/**
 * Hook that configures the global apiClient with Clerk authentication.
 * This should be called once at the app level to set up auth for all API calls.
 * In E2E test mode, skips Clerk authentication.
 */
export function useAuthenticatedApi() {
  const { getToken } = useAuth()

  useEffect(() => {
    // Skip auth injection in E2E test mode
    if (isE2ETestMode()) {
      console.log('[Auth] E2E test mode detected, skipping Clerk token injection')
      return
    }

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
