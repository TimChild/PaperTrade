/**
 * Axios client instance for API calls
 */
import axios, { AxiosError } from 'axios'
import type { ErrorResponse } from './types'

// Use relative URL in production (proxied by nginx), localhost in development
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.MODE === 'production'
    ? '/api/v1'
    : 'http://localhost:8000/api/v1')

// E2E test mode detection
// In E2E tests, we use a static token that the backend's InMemoryAuthAdapter
// will accept in permissive mode
const isE2EMode = import.meta.env.VITE_E2E_TEST_MODE === 'true'
const E2E_TEST_TOKEN = 'e2e-test-token'

// Global token setter for Clerk authentication
// This will be called from AuthProvider which has access to Clerk's useAuth
let tokenGetter: (() => Promise<string | null>) | null = null

export const setAuthTokenGetter = (getter: () => Promise<string | null>) => {
  tokenGetter = getter
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// Request interceptor to add authentication token
apiClient.interceptors.request.use(
  async (config) => {
    // In E2E test mode, always use a static test token
    if (isE2EMode) {
      config.headers.Authorization = `Bearer ${E2E_TEST_TOKEN}`
      console.log(`[API Client] E2E mode: Using static test token for ${config.method?.toUpperCase()} ${config.url}`)
      return config
    }

    // Get token from Clerk if tokenGetter is set
    if (tokenGetter) {
      try {
        const token = await tokenGetter()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
          // Log token retrieval success for debugging (first/last 10 chars only)
          const tokenPreview = token.length > 20 
            ? `${token.substring(0, 10)}...${token.substring(token.length - 10)}`
            : '[short-token]'
          console.log(`[API Client] Token retrieved for ${config.method?.toUpperCase()} ${config.url}: ${tokenPreview}`)
        } else {
          console.error(
            `[API Client] CRITICAL: No token available for ${config.method?.toUpperCase()} ${config.url}. ` +
            'This will result in 401 Unauthorized. ' +
            'Check that Clerk is properly initialized and user is signed in.'
          )
          // Don't set Authorization header - this will cause 401
          // which is better than sending an invalid token
        }
      } catch (error) {
        console.error(
          `[API Client] CRITICAL: Failed to get auth token for ${config.method?.toUpperCase()} ${config.url}:`,
          error
        )
        // Don't set Authorization header
      }
    } else {
      console.warn(
        `[API Client] WARNING: No tokenGetter set for ${config.method?.toUpperCase()} ${config.url}. ` +
        'Authentication will fail. Check that AuthProvider is mounted.'
      )
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response

      const requestUrl = error.config?.url
      const fullUrl = error.config?.baseURL
        ? `${error.config.baseURL}${requestUrl}`
        : requestUrl

      switch (status) {
        case 401:
          console.error('Unauthorized - authentication required')
          console.error('URL:', fullUrl)
          // TODO: Redirect to login when auth is implemented
          break
        case 403:
          console.error('Forbidden - insufficient permissions')
          console.error('URL:', fullUrl)
          break
        case 404:
          console.error('Resource not found:', data?.detail)
          console.error('URL:', fullUrl)
          console.error('Method:', error.config?.method?.toUpperCase())
          break
        case 500:
          console.error('Server error:', data?.detail)
          console.error('URL:', fullUrl)
          break
        default:
          console.error('API error:', data?.detail || error.message)
          console.error('URL:', fullUrl)
      }
    } else if (error.request) {
      // Request made but no response received
      console.error('Network error - no response from server')
    } else {
      // Error in request setup
      console.error('Request error:', error.message)
    }

    return Promise.reject(error)
  }
)
