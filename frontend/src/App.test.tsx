import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
import App from '@/App'

// Mock Clerk hooks
vi.mock('@clerk/clerk-react', async () => {
  const actual = await vi.importActual('@clerk/clerk-react')
  return {
    ...actual,
    ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useAuth: () => ({
      isLoaded: true,
      isSignedIn: true,
      userId: 'test-user-id',
      getToken: async () => 'mock-token',
    }),
    useUser: () => ({
      isLoaded: true,
      isSignedIn: true,
      user: {
        id: 'test-user-id',
        emailAddresses: [{ emailAddress: 'test@example.com' }],
      },
    }),
    SignedIn: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    SignedOut: () => null,
    UserButton: () => null,
  }
})

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
      <ClerkProvider publishableKey="test">
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
      <ClerkProvider publishableKey="test">
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
      <ClerkProvider publishableKey="test">
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
