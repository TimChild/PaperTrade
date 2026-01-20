/**
 * Tests for toast notification helpers
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'
import { toasts } from './toast'

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('toast utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('tradeBuy', () => {
    it('shows success toast with quantity and ticker', () => {
      toasts.tradeBuy('AAPL', 10)

      expect(toast.success).toHaveBeenCalledWith('Bought 10 shares of AAPL')
    })

    it('uses singular "share" for quantity of 1', () => {
      toasts.tradeBuy('AAPL', 1)

      expect(toast.success).toHaveBeenCalledWith('Bought 1 share of AAPL')
    })

    it('includes price and total when price is provided', () => {
      toasts.tradeBuy('AAPL', 10, 150.25)

      expect(toast.success).toHaveBeenCalledWith(
        'Bought 10 shares of AAPL\n$150.25 per share • Total: $1,502.50'
      )
    })

    it('does not include price when price is 0', () => {
      toasts.tradeBuy('AAPL', 10, 0)

      expect(toast.success).toHaveBeenCalledWith('Bought 10 shares of AAPL')
    })
  })

  describe('tradeSell', () => {
    it('shows success toast with quantity and ticker', () => {
      toasts.tradeSell('AAPL', 10)

      expect(toast.success).toHaveBeenCalledWith('Sold 10 shares of AAPL')
    })

    it('uses singular "share" for quantity of 1', () => {
      toasts.tradeSell('AAPL', 1)

      expect(toast.success).toHaveBeenCalledWith('Sold 1 share of AAPL')
    })

    it('includes price and total when price is provided', () => {
      toasts.tradeSell('AAPL', 10, 150.25)

      expect(toast.success).toHaveBeenCalledWith(
        'Sold 10 shares of AAPL\n$150.25 per share • Total: $1,502.50'
      )
    })
  })

  describe('deposit', () => {
    it('shows success toast with formatted amount', () => {
      toasts.deposit(1000.5)

      expect(toast.success).toHaveBeenCalledWith('Deposited $1,000.50')
    })

    it('does not show toast for invalid amount (NaN)', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      toasts.deposit(NaN)

      expect(toast.success).not.toHaveBeenCalled()
      expect(consoleSpy).toHaveBeenCalledWith('Invalid deposit amount:', NaN)
      consoleSpy.mockRestore()
    })

    it('does not show toast for negative amount', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      toasts.deposit(-100)

      expect(toast.success).not.toHaveBeenCalled()
      expect(consoleSpy).toHaveBeenCalledWith('Invalid deposit amount:', -100)
      consoleSpy.mockRestore()
    })

    it('does not show toast for zero amount', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      toasts.deposit(0)

      expect(toast.success).not.toHaveBeenCalled()
      expect(consoleSpy).toHaveBeenCalledWith('Invalid deposit amount:', 0)
      consoleSpy.mockRestore()
    })
  })

  describe('withdraw', () => {
    it('shows success toast with formatted amount', () => {
      toasts.withdraw(500.75)

      expect(toast.success).toHaveBeenCalledWith('Withdrew $500.75')
    })

    it('does not show toast for invalid amount (NaN)', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      toasts.withdraw(NaN)

      expect(toast.success).not.toHaveBeenCalled()
      expect(consoleSpy).toHaveBeenCalledWith('Invalid withdrawal amount:', NaN)
      consoleSpy.mockRestore()
    })

    it('does not show toast for negative amount', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      toasts.withdraw(-50)

      expect(toast.success).not.toHaveBeenCalled()
      expect(consoleSpy).toHaveBeenCalledWith('Invalid withdrawal amount:', -50)
      consoleSpy.mockRestore()
    })
  })

  describe('tradeError', () => {
    it('shows error toast with message', () => {
      toasts.tradeError('Insufficient funds')

      expect(toast.error).toHaveBeenCalledWith('Insufficient funds')
    })
  })

  describe('portfolioCreated', () => {
    it('shows success toast with portfolio name', () => {
      toasts.portfolioCreated('My Portfolio')

      expect(toast.success).toHaveBeenCalledWith(
        'Portfolio "My Portfolio" created'
      )
    })
  })

  describe('portfolioDeleted', () => {
    it('shows success toast for deletion', () => {
      toasts.portfolioDeleted()

      expect(toast.success).toHaveBeenCalledWith(
        'Portfolio deleted successfully'
      )
    })
  })

  describe('portfolioDeleteError', () => {
    it('shows error toast for deletion failure', () => {
      toasts.portfolioDeleteError()

      expect(toast.error).toHaveBeenCalledWith(
        'Failed to delete portfolio. Please try again.'
      )
    })
  })
})
