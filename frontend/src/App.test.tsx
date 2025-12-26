import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
  it('renders without crashing', () => {
    const queryClient = createTestQueryClient()
    
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    expect(screen.getByText('PaperTrade')).toBeInTheDocument()
  })

  it('displays welcome message', () => {
    const queryClient = createTestQueryClient()
    
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    expect(screen.getByText(/Welcome to PaperTrade/i)).toBeInTheDocument()
  })

  it('includes system status section', () => {
    const queryClient = createTestQueryClient()
    
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    )

    expect(screen.getByText('System Status')).toBeInTheDocument()
  })
})
