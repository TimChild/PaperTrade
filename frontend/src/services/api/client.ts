/**
 * Axios client instance for API calls
 */
import axios, { AxiosError } from 'axios'
import type { ErrorResponse } from './types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Default user ID for mock authentication (Phase 1)
// TODO: Replace with real authentication in Phase 2
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': DEFAULT_USER_ID, // Mock authentication header
  },
  timeout: 10000,
})

// Request interceptor (for future auth token injection)
apiClient.interceptors.request.use(
  (config) => {
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

      switch (status) {
        case 401:
          console.error('Unauthorized - authentication required')
          // TODO: Redirect to login when auth is implemented
          break
        case 403:
          console.error('Forbidden - insufficient permissions')
          break
        case 404:
          console.error('Resource not found:', data?.detail)
          break
        case 500:
          console.error('Server error:', data?.detail)
          break
        default:
          console.error('API error:', data?.detail || error.message)
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
