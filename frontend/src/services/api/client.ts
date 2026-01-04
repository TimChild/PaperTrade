/**
 * Axios client instance for API calls
 */
import axios, { AxiosError } from 'axios'
import type { ErrorResponse } from './types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    // Log the full URL for debugging (especially useful in CI)
    const fullUrl = `${config.baseURL}${config.url}`
    console.log(`[API Request] ${config.method?.toUpperCase()} ${fullUrl}`)
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
