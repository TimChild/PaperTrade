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
    // Get token from Clerk if tokenGetter is set
    if (tokenGetter) {
      try {
        const token = await tokenGetter()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } catch (error) {
        console.error('Failed to get auth token:', error)
      }
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
