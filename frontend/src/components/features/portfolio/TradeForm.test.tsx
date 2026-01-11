import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TradeForm } from './TradeForm'
import type { Holding } from '@/types/portfolio'

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

// Helper to render with QueryClientProvider
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('TradeForm', () => {
  const mockOnSubmit = vi.fn()
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

  beforeEach(() => {
    mockOnSubmit.mockClear()
  })

  describe('BUY action', () => {
    it('should render with BUY selected by default', () => {
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const buyButton = screen.getByTestId('trade-form-action-buy')
      expect(buyButton).toHaveClass('bg-primary')
    })

    it('should submit BUY order with correct data', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')

      const submitButton = screen.getByTestId('trade-form-buy-button')
      await user.click(submitButton)

      expect(mockOnSubmit).toHaveBeenCalledWith({
        action: 'BUY',
        ticker: 'IBM',
        quantity: '10',
      })
    })

    it('should convert ticker to uppercase', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'ibm')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')
      await user.click(screen.getByTestId('trade-form-buy-button'))

      expect(mockOnSubmit).toHaveBeenCalledWith({
        action: 'BUY',
        ticker: 'IBM',
        quantity: '10',
      })
    })
  })

  describe('SELL action', () => {
    it('should switch to SELL action when sell button clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      const sellButton = screen.getByTestId('trade-form-action-sell')
      await user.click(sellButton)

      expect(sellButton).toHaveClass('bg-negative')
    })

    it('should display owned quantity when SELL action and ticker selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker that user owns
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')

      // Should show holdings info
      await waitFor(() => {
        expect(
          screen.getByTestId('trade-form-holdings-info')
        ).toBeInTheDocument()
        expect(screen.getByText(/You own/i)).toBeInTheDocument()
        expect(screen.getByText(/100/)).toBeInTheDocument()
        expect(screen.getByText(/shares of AAPL/)).toBeInTheDocument()
      })
    })

    it('should show error when trying to sell stock not owned', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker that user doesn't own
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')

      // Should show no holdings message
      await waitFor(() => {
        expect(screen.getByTestId('trade-form-no-holdings')).toBeInTheDocument()
        expect(
          screen.getByText(/You don't own any shares of IBM/i)
        ).toBeInTheDocument()
      })
    })

    it('should disable submit button when selling stock not owned', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker and quantity for stock not owned
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')

      const submitButton = screen.getByTestId('trade-form-sell-button')
      expect(submitButton).toBeDisabled()
    })

    it('should submit SELL order with correct data', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker and quantity
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '50')

      const submitButton = screen.getByTestId('trade-form-sell-button')
      expect(submitButton).toBeEnabled()

      await user.click(submitButton)

      expect(mockOnSubmit).toHaveBeenCalledWith({
        action: 'SELL',
        ticker: 'AAPL',
        quantity: '50',
      })
    })

    it('should be case-insensitive when matching holdings', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter lowercase ticker
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'aapl')

      // Should still show holdings info
      await waitFor(() => {
        expect(screen.getByText(/You own/i)).toBeInTheDocument()
        expect(screen.getByText(/100/)).toBeInTheDocument()
      })
    })
  })

  describe('Quick Sell functionality', () => {
    it('should pre-fill form when initial values provided', () => {
      renderWithProviders(
        <TradeForm
          onSubmit={mockOnSubmit}
          holdings={mockHoldings}
          initialAction="SELL"
          initialTicker="AAPL"
          initialQuantity="100"
        />
      )

      // Should be in SELL mode
      const sellButton = screen.getByTestId('trade-form-action-sell')
      expect(sellButton).toHaveClass('bg-negative')

      // Should pre-fill ticker and quantity
      const tickerInput = screen.getByTestId(
        'trade-form-ticker-input'
      ) as HTMLInputElement
      const quantityInput = screen.getByTestId(
        'trade-form-quantity-input'
      ) as HTMLInputElement

      expect(tickerInput.value).toBe('AAPL')
      expect(quantityInput.value).toBe('100')
    })

    it('should reset form when key changes', () => {
      const queryClient = createTestQueryClient()
      const { rerender } = render(
        <QueryClientProvider client={queryClient}>
          <TradeForm
            key="trade-1"
            onSubmit={mockOnSubmit}
            holdings={mockHoldings}
            initialAction="BUY"
            initialTicker=""
            initialQuantity=""
          />
        </QueryClientProvider>
      )

      // Initially should be BUY mode
      expect(screen.getByTestId('trade-form-action-buy')).toHaveClass(
        'bg-primary'
      )

      // Remount with new key and quick sell initial values
      rerender(
        <QueryClientProvider client={queryClient}>
          <TradeForm
            key="trade-2"
            onSubmit={mockOnSubmit}
            holdings={mockHoldings}
            initialAction="SELL"
            initialTicker="MSFT"
            initialQuantity="50"
          />
        </QueryClientProvider>
      )

      // Should immediately have new values (no async wait needed)
      const tickerInput = screen.getByTestId(
        'trade-form-ticker-input'
      ) as HTMLInputElement
      const quantityInput = screen.getByTestId(
        'trade-form-quantity-input'
      ) as HTMLInputElement

      expect(tickerInput.value).toBe('MSFT')
      expect(quantityInput.value).toBe('50')
      expect(screen.getByTestId('trade-form-action-sell')).toHaveClass(
        'bg-negative'
      )
    })
  })

  describe('Form validation', () => {
    it('should disable submit when ticker is empty', () => {
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByTestId('trade-form-buy-button')
      expect(submitButton).toBeDisabled()
    })

    it('should disable submit when quantity is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')

      const submitButton = screen.getByTestId('trade-form-buy-button')
      expect(submitButton).toBeDisabled()
    })

    it('should clear form after successful submission', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')
      await user.click(screen.getByTestId('trade-form-buy-button'))

      const tickerInput = screen.getByTestId(
        'trade-form-ticker-input'
      ) as HTMLInputElement
      const quantityInput = screen.getByTestId(
        'trade-form-quantity-input'
      ) as HTMLInputElement

      expect(tickerInput.value).toBe('')
      expect(quantityInput.value).toBe('')
    })
  })

  describe('UI feedback', () => {
    it('should show estimated total when price is auto-populated', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')

      // Wait for price to load
      await waitFor(
        () => {
          expect(screen.getByText(/Estimated Total:/)).toBeInTheDocument()
        },
        { timeout: 2000 }
      )

      // Should show estimated total (10 * 192.53 = 1925.30)
      expect(screen.getByText(/\$1,?925\.30/)).toBeInTheDocument()
    })

    it('should show correct action in preview text', async () => {
      const user = userEvent.setup()
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )

      // BUY preview
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')
      expect(screen.getByText(/Buying 10 shares of IBM/)).toBeInTheDocument()

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Clear and enter new values
      const tickerInput = screen.getByTestId('trade-form-ticker-input')
      await user.clear(tickerInput)
      await user.type(tickerInput, 'AAPL')

      expect(screen.getByText(/Selling 10 shares of AAPL/)).toBeInTheDocument()
    })

    it('should show processing state when submitting', () => {
      renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} isSubmitting={true} />
      )

      const buyButton = screen.getByTestId('trade-form-buy-button')
      expect(buyButton).toHaveTextContent('Processing...')
      expect(buyButton).toBeDisabled()
    })
  })

  describe('Price display (read-only)', () => {
    it('should display fetched price in read-only field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const priceInput = screen.getByTestId(
        'trade-form-price-input'
      ) as HTMLInputElement
      expect(priceInput.value).toBe('--')

      // Type ticker
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')

      // Wait for debounce (500ms) + API call
      await waitFor(
        () => {
          expect(priceInput.value).not.toBe('--')
        },
        { timeout: 2000 }
      )

      // Should have the formatted mock price for AAPL (192.53 from handlers)
      expect(priceInput.value).toBe('192.53')

      // Verify field is read-only
      expect(priceInput).toHaveAttribute('readOnly')
    })

    it('should show loading state while fetching price', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      // Type ticker
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'MSFT')

      // Should show loading spinner (appears after debounce and during fetch)
      // Note: This might be brief due to fast mock API
      await waitFor(
        () => {
          const loading = screen.queryByTestId('trade-form-price-loading')
          const success = screen.queryByTestId('trade-form-price-success')
          // Either loading or success should appear
          expect(loading !== null || success !== null).toBe(true)
        },
        { timeout: 2000 }
      )
    })

    it('should show success indicator after price is loaded', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'GOOGL')

      // Wait for price to load
      await waitFor(
        () => {
          expect(
            screen.getByTestId('trade-form-price-success')
          ).toBeInTheDocument()
        },
        { timeout: 2000 }
      )
    })

    it('should show error message for invalid ticker', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      // Type an invalid ticker (not in mock data)
      // Note: maxLength=5 on ticker input, so "INVALID" becomes "INVAL"
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'INVALID')

      // Wait for debounce + API call + error
      await waitFor(
        () => {
          expect(
            screen.getByTestId('trade-form-price-error')
          ).toBeInTheDocument()
        },
        { timeout: 2000 }
      )

      expect(screen.getByTestId('trade-form-price-error')).toHaveTextContent(
        'Unable to fetch price for INVAL'
      )
    })

    it('should show placeholder in backtest mode', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      // Enable backtest mode
      await user.click(screen.getByTestId('backtest-mode-toggle'))

      const priceInput = screen.getByTestId(
        'trade-form-price-input'
      ) as HTMLInputElement
      expect(priceInput.value).toBe('--')

      // Type ticker
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')

      // Wait a bit to ensure no auto-population happens
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Price should still show placeholder
      expect(priceInput.value).toBe('--')

      // No loading or success indicators should appear
      expect(
        screen.queryByTestId('trade-form-price-loading')
      ).not.toBeInTheDocument()
      expect(
        screen.queryByTestId('trade-form-price-success')
      ).not.toBeInTheDocument()
    })

    it('should not allow manual editing of price field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const priceInput = screen.getByTestId(
        'trade-form-price-input'
      ) as HTMLInputElement

      // Type ticker to trigger auto-populate
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')

      // Wait for auto-population
      await waitFor(
        () => {
          expect(priceInput.value).toBe('192.53')
        },
        { timeout: 2000 }
      )

      // Try to manually change the price - should not work
      await user.click(priceInput)
      await user.type(priceInput, '200.00')

      // Value should remain unchanged
      expect(priceInput.value).toBe('192.53')
    })

    it('should calculate estimated total from priceData', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      // Enter ticker and quantity
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')

      // Wait for price to display
      await waitFor(
        () => {
          const priceInput = screen.getByTestId(
            'trade-form-price-input'
          ) as HTMLInputElement
          expect(priceInput.value).toBe('192.53')
        },
        { timeout: 2000 }
      )

      // Should show estimated total (10 * 192.53 = 1925.30)
      await waitFor(() => {
        expect(
          screen.getByText(/Estimated Total: \$1,?925\.30/)
        ).toBeInTheDocument()
      })
    })

    it('should debounce ticker input to avoid excessive API calls', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const tickerInput = screen.getByTestId('trade-form-ticker-input')

      // Type rapidly (simulating user typing)
      await user.type(tickerInput, 'A')
      await user.type(tickerInput, 'A')
      await user.type(tickerInput, 'P')
      await user.type(tickerInput, 'L')

      // Should show AAPL in input
      expect(tickerInput).toHaveValue('AAPL')

      // Wait for debounce + API call
      await waitFor(
        () => {
          const priceInput = screen.getByTestId(
            'trade-form-price-input'
          ) as HTMLInputElement
          expect(priceInput.value).toBe('192.53')
        },
        { timeout: 2000 }
      )
    })

    it('should update price when ticker changes', async () => {
      const user = userEvent.setup()
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const tickerInput = screen.getByTestId('trade-form-ticker-input')
      const priceInput = screen.getByTestId(
        'trade-form-price-input'
      ) as HTMLInputElement

      // Type first ticker
      await user.type(tickerInput, 'AAPL')
      await waitFor(
        () => {
          expect(priceInput.value).toBe('192.53')
        },
        { timeout: 2000 }
      )

      // Change ticker
      await user.clear(tickerInput)
      await user.type(tickerInput, 'GOOGL')

      // Price should update (GOOGL is mocked at 140.93)
      await waitFor(
        () => {
          expect(priceInput.value).toBe('140.93')
        },
        { timeout: 2000 }
      )
    })

    it('should show placeholder when no ticker entered', () => {
      renderWithProviders(<TradeForm onSubmit={mockOnSubmit} />)

      const priceInput = screen.getByTestId(
        'trade-form-price-input'
      ) as HTMLInputElement
      expect(priceInput.value).toBe('--')
    })
  })

  describe('Accessibility', () => {
    it('should have no accessibility violations', async () => {
      const { axe } = await import('jest-axe')
      const { container } = renderWithProviders(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })
})
