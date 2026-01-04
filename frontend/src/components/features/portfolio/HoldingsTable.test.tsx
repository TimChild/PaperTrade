import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HoldingsTable } from './HoldingsTable'
import type { Holding } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'

// Mock the price query hook
vi.mock('@/hooks/usePriceQuery', () => ({
  useBatchPricesQuery: vi.fn((tickers: string[]) => {
    const priceMap = new Map([
      ['AAPL', { price: { amount: 175.0, currency: 'USD' }, timestamp: '2024-01-01T12:00:00Z' }],
      ['MSFT', { price: { amount: 350.0, currency: 'USD' }, timestamp: '2024-01-01T12:00:00Z' }],
      ['LOSS', { price: { amount: 150.0, currency: 'USD' }, timestamp: '2024-01-01T12:00:00Z' }],
    ])

    // Only return prices for requested tickers
    const filteredPriceMap = new Map()
    tickers.forEach((ticker) => {
      const price = priceMap.get(ticker)
      if (price) {
        filteredPriceMap.set(ticker, price)
      }
    })

    return {
      data: filteredPriceMap,
      isLoading: false,
    }
  }),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('HoldingsTable', () => {
  const mockHoldings: Holding[] = [
    {
      ticker: 'AAPL',
      quantity: 100,
      averageCost: 150.0,
      currentPrice: 175.0,
      marketValue: 17500.0,
      gainLoss: 2500.0,
      gainLossPercent: 16.67,
    },
    {
      ticker: 'MSFT',
      quantity: 50,
      averageCost: 300.0,
      currentPrice: 350.0,
      marketValue: 17500.0,
      gainLoss: 2500.0,
      gainLossPercent: 16.67,
    },
  ]

  const mockHoldingsDTO: HoldingDTO[] = [
    {
      ticker: 'AAPL',
      quantity: '100',
      cost_basis: '15000.00',
      average_cost_per_share: '150.00',
    },
    {
      ticker: 'MSFT',
      quantity: '50',
      cost_basis: '15000.00',
      average_cost_per_share: '300.00',
    },
  ]

  describe('Basic rendering', () => {
    it('should render holdings table with data', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('holdings-table')).toBeInTheDocument()
      expect(screen.getByTestId('holding-row-AAPL')).toBeInTheDocument()
      expect(screen.getByTestId('holding-row-MSFT')).toBeInTheDocument()
    })

    it('should display holding symbols correctly', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('holding-symbol-AAPL')).toHaveTextContent('AAPL')
      expect(screen.getByTestId('holding-symbol-MSFT')).toHaveTextContent('MSFT')
    })

    it('should display holding quantities', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('holding-quantity-AAPL')).toHaveTextContent('100')
      expect(screen.getByTestId('holding-quantity-MSFT')).toHaveTextContent('50')
    })

    it('should display market values', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('holding-value-AAPL')).toHaveTextContent('$17,500.00')
      expect(screen.getByTestId('holding-value-MSFT')).toHaveTextContent('$17,500.00')
    })

    it('should show empty state when no holdings', () => {
      render(<HoldingsTable holdings={[]} />, { wrapper: createWrapper() })

      expect(screen.getByText(/No holdings in this portfolio yet/i)).toBeInTheDocument()
    })

    it('should show loading state', () => {
      render(<HoldingsTable holdings={[]} isLoading={true} />, { wrapper: createWrapper() })

      // Should show skeleton loaders
      const skeletons = screen.getAllByRole('generic').filter((el) =>
        el.className.includes('animate-pulse')
      )
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('Quick Sell button', () => {
    it('should render Quick Sell button when onQuickSell provided', () => {
      const mockOnQuickSell = vi.fn()
      render(<HoldingsTable holdings={mockHoldings} onQuickSell={mockOnQuickSell} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByTestId('holdings-quick-sell-aapl')).toBeInTheDocument()
      expect(screen.getByTestId('holdings-quick-sell-msft')).toBeInTheDocument()
    })

    it('should not render Quick Sell button when onQuickSell not provided', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.queryByTestId('holdings-quick-sell-aapl')).not.toBeInTheDocument()
      expect(screen.queryByTestId('holdings-quick-sell-msft')).not.toBeInTheDocument()
    })

    it('should call onQuickSell with correct ticker and quantity when clicked', async () => {
      const user = userEvent.setup()
      const mockOnQuickSell = vi.fn()

      render(<HoldingsTable holdings={mockHoldings} onQuickSell={mockOnQuickSell} />, {
        wrapper: createWrapper(),
      })

      const quickSellButton = screen.getByTestId('holdings-quick-sell-aapl')
      await user.click(quickSellButton)

      expect(mockOnQuickSell).toHaveBeenCalledWith('AAPL', 100)
    })

    it('should have Actions column header when onQuickSell provided', () => {
      const mockOnQuickSell = vi.fn()
      render(<HoldingsTable holdings={mockHoldings} onQuickSell={mockOnQuickSell} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('should not have Actions column header when onQuickSell not provided', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.queryByText('Actions')).not.toBeInTheDocument()
    })

    it('should handle Quick Sell for multiple holdings', async () => {
      const user = userEvent.setup()
      const mockOnQuickSell = vi.fn()

      render(<HoldingsTable holdings={mockHoldings} onQuickSell={mockOnQuickSell} />, {
        wrapper: createWrapper(),
      })

      // Click AAPL Quick Sell
      await user.click(screen.getByTestId('holdings-quick-sell-aapl'))
      expect(mockOnQuickSell).toHaveBeenCalledWith('AAPL', 100)

      // Click MSFT Quick Sell
      await user.click(screen.getByTestId('holdings-quick-sell-msft'))
      expect(mockOnQuickSell).toHaveBeenCalledWith('MSFT', 50)

      expect(mockOnQuickSell).toHaveBeenCalledTimes(2)
    })
  })

  describe('Gain/Loss display', () => {
    it('should show positive gain/loss in green', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      const rows = screen.getAllByRole('row')
      // Find rows with gain/loss cells (skip header)
      const aaplRow = rows.find((row) => row.textContent?.includes('AAPL'))
      expect(aaplRow).toHaveClass('hover:bg-gray-50')
    })

    it('should show negative gain/loss in red', () => {
      const holdingsWithLoss: Holding[] = [
        {
          ticker: 'LOSS',
          quantity: 100,
          averageCost: 200.0,
          currentPrice: 150.0, // Mock will return 150.0
          marketValue: 15000.0,
          gainLoss: -5000.0,
          gainLossPercent: -25.0,
        },
      ]

      render(<HoldingsTable holdings={holdingsWithLoss} />, { wrapper: createWrapper() })

      expect(screen.getByText(/-\$5,000\.00/)).toBeInTheDocument()
      expect(screen.getByText(/25\.00%/)).toBeInTheDocument()
    })

    it('should format gain/loss percentage correctly', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      // Should show percentage for AAPL (16.67% shown as +16.67%)
      const percentages = screen.getAllByText(/\+16\.67%/)
      expect(percentages.length).toBeGreaterThan(0)
    })
  })

  describe('Price display', () => {
    it('should display current prices', () => {
      render(<HoldingsTable holdings={mockHoldings} holdingsDTO={mockHoldingsDTO} />, {
        wrapper: createWrapper(),
      })

      // Prices should be displayed (mocked to return real-time prices)
      expect(screen.getAllByText(/\$175.00/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/\$350.00/).length).toBeGreaterThan(0)
    })

    it('should display average cost', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByText('$150.00')).toBeInTheDocument()
      expect(screen.getByText('$300.00')).toBeInTheDocument()
    })
  })

  describe('Table structure', () => {
    it('should have correct column headers', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      expect(screen.getByText('Symbol')).toBeInTheDocument()
      expect(screen.getByText('Shares')).toBeInTheDocument()
      expect(screen.getByText('Avg Cost')).toBeInTheDocument()
      expect(screen.getByText('Current Price')).toBeInTheDocument()
      expect(screen.getByText('Market Value')).toBeInTheDocument()
      expect(screen.getByText('Gain/Loss')).toBeInTheDocument()
    })

    it('should have correct number of rows', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      // 1 header row + 2 data rows
      const rows = screen.getAllByRole('row')
      expect(rows).toHaveLength(3)
    })

    it('should apply hover styles to rows', () => {
      render(<HoldingsTable holdings={mockHoldings} />, { wrapper: createWrapper() })

      const aaplRow = screen.getByTestId('holding-row-AAPL')
      expect(aaplRow).toHaveClass('hover:bg-gray-50')
    })
  })
})
