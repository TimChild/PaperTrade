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

// Debug logging helper for E2E tests
// Enable debug logging if:
// 1. URL has e2e-debug parameter
// 2. Running in Playwright test environment
// 3. VITE_E2E_DEBUG environment variable is set
const isE2ETest =
  (typeof window !== 'undefined' && window.location.search.includes('e2e-debug')) ||
  import.meta.env.VITE_E2E_DEBUG === 'true'
const isPlaywrightTest =
  import.meta.env.MODE === 'test' ||
  (typeof process !== 'undefined' && process.env.PLAYWRIGHT_TEST)

// Always log in E2E environment for debugging
const shouldDebugLog = isE2ETest || isPlaywrightTest

function debugLog(message: string, ...args: unknown[]): void {
  if (shouldDebugLog) {
    console.log(`[API Client Debug] ${message}`, ...args)
  }
}

// Global token setter for Clerk authentication
// This will be called from AuthProvider which has access to Clerk's useAuth
let tokenGetter: (() => Promise<string | null>) | null = null

export const setAuthTokenGetter = (getter: () => Promise<string | null>) => {
  tokenGetter = getter
  debugLog('Auth token getter configured')
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

debugLog('API client created', { baseURL: API_BASE_URL })

// Request interceptor to add authentication token
apiClient.interceptors.request.use(
  async (config) => {
    debugLog('Request starting', {
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
    })

    // Get token from Clerk if tokenGetter is set
    if (tokenGetter) {
      try {
        const token = await tokenGetter()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
          debugLog('Auth token attached', {
            tokenPrefix: token.substring(0, 8) + '...',
            tokenSuffix: '...' + token.substring(token.length - 8),
            tokenLength: token.length,
          })
        } else {
          debugLog('No auth token available from tokenGetter')
        }
      } catch (error) {
        console.error('Failed to get auth token:', error)
        debugLog('Failed to get auth token', { error })
      }
    } else {
      debugLog('No tokenGetter configured')
    }

    return config
  },
  (error) => {
    debugLog('Request interceptor error', { error })
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    debugLog('Response received', {
      status: response.status,
      statusText: response.statusText,
      url: response.config.url,
      dataPreview: JSON.stringify(response.data).substring(0, 100),
    })
    return response
  },
  (error: AxiosError<ErrorResponse>) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response

      const requestUrl = error.config?.url
      const fullUrl = error.config?.baseURL
        ? `${error.config.baseURL}${requestUrl}`
        : requestUrl

      debugLog('Response error', {
        status,
        statusText: error.response.statusText,
        url: fullUrl,
        method: error.config?.method?.toUpperCase(),
        data,
        headers: error.response.headers,
      })

      switch (status) {
        case 401:
          console.error('Unauthorized - authentication required')
          console.error('URL:', fullUrl)
          debugLog('401 Unauthorized - check authentication token')
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
      debugLog('Network error - no response', {
        error: error.message,
        code: error.code,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      })
    } else {
      // Error in request setup
      console.error('Request error:', error.message)
      debugLog('Request setup error', { error: error.message })
    }

    return Promise.reject(error)
  }
)
