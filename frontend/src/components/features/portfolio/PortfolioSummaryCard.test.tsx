import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
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

describe('PortfolioSummaryCard', () => {
  it('renders portfolio name', () => {
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />)
    expect(screen.getByText('Test Portfolio')).toBeInTheDocument()
  })

  it('displays total value formatted as currency', () => {
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />)
    expect(screen.getByText('$156,750.00')).toBeInTheDocument()
  })

  it('displays daily change with positive formatting', () => {
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />)
    expect(screen.getByText(/\+\$2,450\.00/)).toBeInTheDocument()
    expect(screen.getByText(/\+1\.59%/)).toBeInTheDocument()
  })

  it('displays cash balance', () => {
    render(<PortfolioSummaryCard portfolio={mockPortfolio} />)
    expect(screen.getByText('$25,000.00')).toBeInTheDocument()
  })

  it('shows loading state when isLoading is true', () => {
    render(<PortfolioSummaryCard portfolio={mockPortfolio} isLoading={true} />)
    expect(screen.queryByText('Test Portfolio')).not.toBeInTheDocument()
  })

  it('displays negative change correctly', () => {
    const negativePortfolio = {
      ...mockPortfolio,
      dailyChange: -1500,
      dailyChangePercent: -0.0096,
    }
    render(<PortfolioSummaryCard portfolio={negativePortfolio} />)
    expect(screen.getByText(/-\$1,500\.00/)).toBeInTheDocument()
  })
})
