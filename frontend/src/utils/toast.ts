/**
 * Centralized toast notification helpers
 * Provides consistent, reusable toast notifications across the application
 */
import toast from 'react-hot-toast'
import { formatCurrency } from './formatters'

export const toasts = {
  /**
   * Show success toast for BUY trade
   */
  tradeBuy: (ticker: string, quantity: number, price?: number): void => {
    const shares = quantity === 1 ? 'share' : 'shares'
    let message = `Bought ${quantity} ${shares} of ${ticker}`

    if (price && price > 0) {
      const total = quantity * price
      message += `\n${formatCurrency(price)} per share • Total: ${formatCurrency(total)}`
    }

    toast.success(message)
  },

  /**
   * Show success toast for SELL trade
   */
  tradeSell: (ticker: string, quantity: number, price?: number): void => {
    const shares = quantity === 1 ? 'share' : 'shares'
    let message = `Sold ${quantity} ${shares} of ${ticker}`

    if (price && price > 0) {
      const total = quantity * price
      message += `\n${formatCurrency(price)} per share • Total: ${formatCurrency(total)}`
    }

    toast.success(message)
  },

  /**
   * Show success toast for deposit
   */
  deposit: (amount: number): void => {
    toast.success(`Deposited ${formatCurrency(amount)}`)
  },

  /**
   * Show success toast for withdrawal
   */
  withdraw: (amount: number): void => {
    toast.success(`Withdrew ${formatCurrency(amount)}`)
  },

  /**
   * Show error toast for trade failure
   */
  tradeError: (message: string): void => {
    toast.error(`Trade failed: ${message}`)
  },

  /**
   * Show success toast for portfolio creation
   */
  portfolioCreated: (name: string): void => {
    toast.success(`Portfolio "${name}" created`)
  },

  /**
   * Show success toast for portfolio deletion
   */
  portfolioDeleted: (): void => {
    toast.success('Portfolio deleted successfully')
  },

  /**
   * Show error toast for portfolio deletion failure
   */
  portfolioDeleteError: (): void => {
    toast.error('Failed to delete portfolio. Please try again.')
  },
}
