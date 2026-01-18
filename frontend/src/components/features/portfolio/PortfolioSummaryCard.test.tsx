import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import type { Portfolio } from '@/types/portfolio'

const mockPortfolio: Portfolio = {
  id: 'test-portfolio',
  name: 'Test Portfolio',
  userId: 'user-1',
  cashBalance: 25000,
  totalValue: 156750,
  dailyChange: 2450,
  dailyChangePercent: 0.0159,
  createdAt: '2024-01-15T10:00:00Z',
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('PortfolioSummaryCard', () => {
  it('renders portfolio name', () => {
    const Wrapper = createWrapper()
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText('Test Portfolio')).toBeInTheDocument()
  })

  it('displays total value formatted as currency', () => {
    const Wrapper = createWrapper()
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />, {
      wrapper: Wrapper,
    })
    // Backend-calculated total value should be displayed
    const totalValueElement = screen.getByTestId('portfolio-total-value')
    expect(totalValueElement).toHaveTextContent('$156,750.00')
  })

  it('displays daily change with positive formatting', () => {
    const Wrapper = createWrapper()
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText(/\+\$2,450\.00/)).toBeInTheDocument()
    expect(screen.getByText(/\+1\.59%/)).toBeInTheDocument()
  })

  it('displays cash balance', () => {
    const Wrapper = createWrapper()
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />, {
      wrapper: Wrapper,
    })
    const cashBalanceElement = screen.getByText('Cash Balance').parentElement
    expect(cashBalanceElement).toHaveTextContent('$25,000.00')
  })

  it('shows loading state when isLoading is true', () => {
    const Wrapper = createWrapper()
    render(
      <PortfolioSummaryCard portfolio={mockPortfolio} isLoading={true} />,
      {
        wrapper: Wrapper,
      }
    )
    expect(screen.queryByText('Test Portfolio')).not.toBeInTheDocument()
  })

  it('displays holdings value calculated from total minus cash', () => {
    const Wrapper = createWrapper()
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />, {
      wrapper: Wrapper,
    })
    // Holdings value = totalValue - cashBalance = 156750 - 25000 = 131750
    expect(screen.getByText('Holdings Value')).toBeInTheDocument()
    const holdingsValueText = screen.getByText('$131,750.00')
    expect(holdingsValueText).toBeInTheDocument()
  })

  it('does not display holdings value section when holdings value is zero', () => {
    const Wrapper = createWrapper()
    const portfolioWithNoHoldings = {
      ...mockPortfolio,
      totalValue: 25000, // Same as cash balance
    }
    render(<PortfolioSummaryCard portfolio={portfolioWithNoHoldings} />, {
      wrapper: Wrapper,
    })
    expect(screen.queryByText('Holdings Value')).not.toBeInTheDocument()
  })

  it('displays negative change correctly', () => {
    const Wrapper = createWrapper()
    const negativePortfolio = {
      ...mockPortfolio,
      dailyChange: -1500,
      dailyChangePercent: -0.0096,
    }
    render(<PortfolioSummaryCard portfolio={negativePortfolio} />, {
      wrapper: Wrapper,
    })
    expect(screen.getByText(/-\$1,500\.00/)).toBeInTheDocument()
  })
})
