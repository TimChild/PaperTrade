import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HealthCheck } from '@/components/HealthCheck'
import * as healthHook from '@/hooks/useHealthCheck'
import type { UseQueryResult } from '@tanstack/react-query'
import type { HealthResponse } from '@/types/api'

// Create a test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

describe('HealthCheck', () => {
  it('displays loading state', () => {
    vi.spyOn(healthHook, 'useHealthCheck').mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as UseQueryResult<HealthResponse>)

    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <HealthCheck />
      </QueryClientProvider>
    )

    expect(screen.getByText(/Checking backend connection/i)).toBeInTheDocument()
  })

  it('displays error state when backend is unavailable', () => {
    vi.spyOn(healthHook, 'useHealthCheck').mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
    } as UseQueryResult<HealthResponse>)

    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <HealthCheck />
      </QueryClientProvider>
    )

    expect(screen.getByText(/Backend unavailable/i)).toBeInTheDocument()
  })

  it('displays success state when backend is connected', () => {
    vi.spyOn(healthHook, 'useHealthCheck').mockReturnValue({
      data: { status: 'healthy' },
      isLoading: false,
      isError: false,
      error: null,
    } as UseQueryResult<HealthResponse>)

    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <HealthCheck />
      </QueryClientProvider>
    )

    expect(screen.getByText(/Backend connected/i)).toBeInTheDocument()
  })
})
