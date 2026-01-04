import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TradeForm } from './TradeForm'
import type { Holding } from '@/types/portfolio'

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
      render(<TradeForm onSubmit={mockOnSubmit} />)

      const buyButton = screen.getByTestId('trade-form-action-buy')
      expect(buyButton).toHaveClass('bg-blue-600')
    })

    it('should submit BUY order with correct data', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} />)

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
      render(<TradeForm onSubmit={mockOnSubmit} />)

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
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

      const sellButton = screen.getByTestId('trade-form-action-sell')
      await user.click(sellButton)

      expect(sellButton).toHaveClass('bg-negative')
    })

    it('should display owned quantity when SELL action and ticker selected', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker that user owns
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'AAPL')

      // Should show holdings info
      await waitFor(() => {
        expect(screen.getByTestId('trade-form-holdings-info')).toBeInTheDocument()
        expect(screen.getByText(/You own/i)).toBeInTheDocument()
        expect(screen.getByText(/100/)).toBeInTheDocument()
        expect(screen.getByText(/shares of AAPL/)).toBeInTheDocument()
      })
    })

    it('should show error when trying to sell stock not owned', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

      // Switch to SELL
      await user.click(screen.getByTestId('trade-form-action-sell'))

      // Enter ticker that user doesn't own
      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')

      // Should show no holdings message
      await waitFor(() => {
        expect(screen.getByTestId('trade-form-no-holdings')).toBeInTheDocument()
        expect(screen.getByText(/You don't own any shares of IBM/i)).toBeInTheDocument()
      })
    })

    it('should disable submit button when selling stock not owned', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

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
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

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
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

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
    it('should pre-fill form when quickSellData provided', async () => {
      const quickSellData = { ticker: 'AAPL', quantity: 100 }
      render(
        <TradeForm
          onSubmit={mockOnSubmit}
          holdings={mockHoldings}
          quickSellData={quickSellData}
        />
      )

      // Should switch to SELL
      await waitFor(() => {
        const sellButton = screen.getByTestId('trade-form-action-sell')
        expect(sellButton).toHaveClass('bg-negative')
      })

      // Should pre-fill ticker and quantity
      const tickerInput = screen.getByTestId('trade-form-ticker-input') as HTMLInputElement
      const quantityInput = screen.getByTestId('trade-form-quantity-input') as HTMLInputElement

      expect(tickerInput.value).toBe('AAPL')
      expect(quantityInput.value).toBe('100')
    })

    it('should update form when quickSellData changes', async () => {
      const { rerender } = render(
        <TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} quickSellData={null} />
      )

      // Initially should be BUY mode
      expect(screen.getByTestId('trade-form-action-buy')).toHaveClass('bg-blue-600')

      // Update with quick sell data
      const quickSellData = { ticker: 'MSFT', quantity: 50 }
      rerender(
        <TradeForm
          onSubmit={mockOnSubmit}
          holdings={mockHoldings}
          quickSellData={quickSellData}
        />
      )

      await waitFor(() => {
        const tickerInput = screen.getByTestId('trade-form-ticker-input') as HTMLInputElement
        const quantityInput = screen.getByTestId('trade-form-quantity-input') as HTMLInputElement

        expect(tickerInput.value).toBe('MSFT')
        expect(quantityInput.value).toBe('50')
        expect(screen.getByTestId('trade-form-action-sell')).toHaveClass('bg-negative')
      })
    })
  })

  describe('Form validation', () => {
    it('should disable submit when ticker is empty', () => {
      render(<TradeForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByTestId('trade-form-buy-button')
      expect(submitButton).toBeDisabled()
    })

    it('should disable submit when quantity is empty', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')

      const submitButton = screen.getByTestId('trade-form-buy-button')
      expect(submitButton).toBeDisabled()
    })

    it('should clear form after successful submission', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')
      await user.click(screen.getByTestId('trade-form-buy-button'))

      const tickerInput = screen.getByTestId('trade-form-ticker-input') as HTMLInputElement
      const quantityInput = screen.getByTestId('trade-form-quantity-input') as HTMLInputElement

      expect(tickerInput.value).toBe('')
      expect(quantityInput.value).toBe('')
    })
  })

  describe('UI feedback', () => {
    it('should show estimated total when price is provided', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} />)

      await user.type(screen.getByTestId('trade-form-ticker-input'), 'IBM')
      await user.type(screen.getByTestId('trade-form-quantity-input'), '10')
      await user.type(screen.getByTestId('trade-form-price-input'), '150.50')

      expect(screen.getByText(/Estimated Total:/)).toBeInTheDocument()
      expect(screen.getByText(/\$1505\.00/)).toBeInTheDocument()
    })

    it('should show correct action in preview text', async () => {
      const user = userEvent.setup()
      render(<TradeForm onSubmit={mockOnSubmit} holdings={mockHoldings} />)

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
      render(<TradeForm onSubmit={mockOnSubmit} isSubmitting={true} />)

      const buyButton = screen.getByTestId('trade-form-buy-button')
      expect(buyButton).toHaveTextContent('Processing...')
      expect(buyButton).toBeDisabled()
    })
  })
})
