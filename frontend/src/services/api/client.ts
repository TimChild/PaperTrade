/**
 * Axios client instance for API calls
 */
import axios, { AxiosError } from 'axios'
import type { ErrorResponse } from './types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

/**
 * Get or create a stable mock user ID for Phase 1.
 * Stored in localStorage to persist across sessions.
 *
 * TODO: Replace with real authentication in Phase 2
 */
function getMockUserId(): string {
  const STORAGE_KEY = 'papertrade_mock_user_id'

  // Check localStorage for existing ID
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return stored
  }

  // Generate new ID and store it
  const newId = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, newId)
  return newId
}

const MOCK_USER_ID = getMockUserId()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': MOCK_USER_ID, // Mock authentication header (persisted in localStorage)
  },
  timeout: 10000,
})

// Request interceptor (for future auth token injection)
apiClient.interceptors.request.use(
  (config) => {
    // Log the full URL for debugging (especially useful in CI)
    const fullUrl = `${config.baseURL}${config.url}`
    console.log(`[API Request] ${config.method?.toUpperCase()} ${fullUrl}`)

    // Add auth token when implemented
    // const token = localStorage.getItem('authToken')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
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
      const fullUrl = error.config?.baseURL ? `${error.config.baseURL}${requestUrl}` : requestUrl

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
