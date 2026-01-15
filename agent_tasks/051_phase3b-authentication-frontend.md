# Task 051: Phase 3b Authentication - Frontend Implementation

**Agent**: frontend-swe
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 1 week
**Dependencies**: Task #050 (Backend auth must be complete)
**Discovery Document**: [agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md](../agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md)

## Objective

Implement authentication UI and state management for Zebu frontend. Enable users to register, login, and access protected routes with JWT token management.

## Context

**Discovery Analysis** (Task #049):
- Current Status: 15% frontend prepared (axios interceptor ready, mock user ID in localStorage)
- Missing: Auth pages, state management, protected routes, token refresh logic
- Prepared Infrastructure: Zustand installed, interceptor pattern ready

**Architecture Reference**: `architecture_plans/phase3-refined/phase3b-authentication.md`

## Prerequisites

**Backend API must be complete** (Task #050):
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- GET /users/me
- Protected endpoints validate JWT tokens

## Implementation Order

### 1. Auth State Management (`src/stores/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean

  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),

      setUser: (user) =>
        set({ user }),

      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'zebu-auth',
      // Only persist refresh token (access token in memory only for security)
      partialize: (state) => ({ refreshToken: state.refreshToken }),
    }
  )
)
```

**Security Notes**:
- Access tokens stored in memory only (not localStorage)
- Refresh tokens persisted to survive page reloads
- Logout clears all auth state

### 2. Auth API Service (`src/services/api/auth.ts`)

```typescript
import { apiClient } from './client'

export interface RegisterRequest {
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  created_at: string
}

export const authApi = {
  register: async (data: RegisterRequest): Promise<void> => {
    await apiClient.post('/auth/register', data)
  },

  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    // FastAPI OAuth2PasswordRequestForm expects form data
    const formData = new URLSearchParams()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)

    const response = await apiClient.post<TokenResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me')
    return response.data
  },
}
```

### 3. Update API Client (`src/services/api/client.ts`)

**Remove mock user ID, add JWT interceptors**:

```typescript
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: Add JWT access token to all requests
apiClient.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState()
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: Refresh token on 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const { refreshToken, setTokens, logout } = useAuthStore.getState()

      if (!refreshToken) {
        logout()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      try {
        // Attempt to refresh tokens
        const tokens = await authApi.refresh(refreshToken)
        setTokens(tokens.access_token, tokens.refresh_token)

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed - logout user
        logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
```

**Remove old mock code**:
- Delete `getMockUserId()` function
- Delete `MOCK_USER_ID` constant
- Remove `X-User-Id` header

### 4. Login Page (`src/pages/Login.tsx`)

```typescript
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/services/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  const { setTokens, setUser } = useAuthStore()

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token)

      // Fetch user profile
      const user = await authApi.getCurrentUser()
      setUser(user)

      navigate('/')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ email, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center">Sign in to Zebu</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </div>

          {loginMutation.isError && (
            <ErrorDisplay error={loginMutation.error} />
          )}

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loginMutation.isPending ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm">
          Don't have an account?{' '}
          <Link to="/register" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
```

### 5. Register Page (`src/pages/Register.tsx`)

```typescript
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/services/api/auth'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'

export function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const navigate = useNavigate()

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: () => {
      // Redirect to login after successful registration
      navigate('/login', {
        state: { message: 'Registration successful! Please sign in.' }
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (password !== confirmPassword) {
      alert('Passwords do not match')
      return
    }

    registerMutation.mutate({ email, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center">Create your account</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
            <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </div>

          {registerMutation.isError && (
            <ErrorDisplay error={registerMutation.error} />
          )}

          <button
            type="submit"
            disabled={registerMutation.isPending}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {registerMutation.isPending ? 'Creating account...' : 'Sign up'}
          </button>
        </form>

        <p className="text-center text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
```

### 6. Protected Route Component (`src/components/auth/ProtectedRoute.tsx`)

```typescript
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
```

### 7. Update Router (`src/App.tsx`)

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Login } from '@/pages/Login'
import { Register } from '@/pages/Register'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
// ... existing imports

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolios/:id"
          element={
            <ProtectedRoute>
              <PortfolioDetail />
            </ProtectedRoute>
          }
        />
        {/* Add ProtectedRoute wrapper to all authenticated pages */}
      </Routes>
    </BrowserRouter>
  )
}
```

### 8. Navigation with Logout (`src/components/layout/Navigation.tsx`)

```typescript
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function Navigation() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="bg-blue-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-xl font-bold">Zebu</h1>

        <div className="flex items-center gap-4">
          <span className="text-sm">{user?.email}</span>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-blue-700 rounded hover:bg-blue-800"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
```

### 9. Auto-Load User on App Start (`src/App.tsx`)

```typescript
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/services/api/auth'

function App() {
  const { isAuthenticated, setUser, logout } = useAuthStore()

  useEffect(() => {
    // If we have a refresh token but no user data, fetch user
    if (isAuthenticated) {
      authApi.getCurrentUser()
        .then(setUser)
        .catch(() => {
          // Token invalid - logout
          logout()
        })
    }
  }, [isAuthenticated, setUser, logout])

  // ... rest of App
}
```

## Testing Strategy

### Unit Tests
- ✅ `authStore.test.ts`: State management (setTokens, logout, persistence)
- ✅ `Login.test.tsx`: Form submission, error handling, navigation
- ✅ `Register.test.tsx`: Form validation, password confirmation
- ✅ `ProtectedRoute.test.tsx`: Redirect when unauthenticated, render when authenticated

### Integration Tests
- ✅ Login flow: enter credentials → call API → store tokens → redirect
- ✅ Registration flow: enter details → call API → redirect to login
- ✅ Protected route: unauthenticated → redirect to login
- ✅ Logout: clear state → redirect to login
- ✅ Token refresh: 401 response → refresh → retry request

### E2E Tests (`tests/e2e/auth.spec.ts`)
```typescript
test('complete authentication flow', async ({ page }) => {
  // Register
  await page.goto('/register')
  await page.fill('[data-testid="email-input"]', 'test@example.com')
  await page.fill('[data-testid="password-input"]', 'password123')
  await page.fill('[data-testid="confirm-password-input"]', 'password123')
  await page.click('[data-testid="register-button"]')

  // Should redirect to login
  await expect(page).toHaveURL('/login')

  // Login
  await page.fill('[data-testid="email-input"]', 'test@example.com')
  await page.fill('[data-testid="password-input"]', 'password123')
  await page.click('[data-testid="login-button"]')

  // Should redirect to home
  await expect(page).toHaveURL('/')

  // Logout
  await page.click('[data-testid="logout-button"]')
  await expect(page).toHaveURL('/login')
})
```

## Success Criteria

1. ✅ Can register new user via /register page
2. ✅ Can login with email/password via /login page
3. ✅ Tokens stored securely (access in memory, refresh in localStorage)
4. ✅ Protected routes redirect to login when unauthenticated
5. ✅ Protected routes accessible when authenticated
6. ✅ Logout clears auth state and redirects to login
7. ✅ Token refresh works automatically on 401 errors
8. ✅ User profile loaded on app start if authenticated
9. ✅ All unit tests passing
10. ✅ E2E auth flow test passing

## Security Notes

- ✅ Access tokens in memory only (cleared on page refresh - acceptable tradeoff)
- ✅ Refresh tokens in localStorage (persistent across page reloads)
- ✅ Password confirmation before registration
- ✅ Password minimum length enforced (8 chars)
- ✅ HTTPS only in production (configure Vite)
- ✅ No sensitive data logged to console

## References

- Architecture: `architecture_plans/phase3-refined/phase3b-authentication.md`
- Discovery: `agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md`
- Copilot Instructions: `.github/copilot-instructions.md`
