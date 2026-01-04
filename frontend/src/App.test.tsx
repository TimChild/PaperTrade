import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
import App from '@/App'

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

describe('App', () => {
  it('renders without crashing', async () => {
    const queryClient = createTestQueryClient()

    render(
      <ClerkProvider publishableKey="test-key">
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ClerkProvider>
    )

    // Wait for data to load (MSW will respond)
    await waitFor(() => {
      expect(screen.getByText('Portfolio Dashboard')).toBeInTheDocument()
    })
  })

  it('displays dashboard page by default', async () => {
    const queryClient = createTestQueryClient()

    render(
      <ClerkProvider publishableKey="test-key">
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ClerkProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Track your investments and performance/i)).toBeInTheDocument()
    })
  })

  it('renders portfolio summary section', async () => {
    const queryClient = createTestQueryClient()

    render(
      <ClerkProvider publishableKey="test-key">
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ClerkProvider>
    )

    // Wait for portfolio data to load
    await waitFor(() => {
      expect(screen.getByText('Test Portfolio')).toBeInTheDocument()
    })
  })
})
