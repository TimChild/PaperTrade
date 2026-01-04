import type {
  Portfolio,
  Holding,
  Transaction,
  TradeRequest,
} from '@/types/portfolio'
import {
  mockPortfolios,
  mockHoldings,
  mockTransactions,
} from '@/mocks/portfolio'

/**
 * Portfolio API service
 * Currently using mock data, will be replaced with real API calls
 */
export const portfolioService = {
  /**
   * Get all portfolios for the current user
   */
  async getAll(): Promise<Portfolio[]> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300))
    return mockPortfolios
  },

  /**
   * Get a single portfolio by ID
   */
  async getById(id: string): Promise<Portfolio> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300))

    const portfolio = mockPortfolios.find((p) => p.id === id)
    if (!portfolio) {
      throw new Error(`Portfolio with id ${id} not found`)
    }
    return portfolio
  },

  /**
   * Get holdings for a portfolio
   */
  async getHoldings(portfolioId: string): Promise<Holding[]> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300))

    return mockHoldings[portfolioId] || []
  },

  /**
   * Get transactions for a portfolio
   */
  async getTransactions(portfolioId: string): Promise<Transaction[]> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300))

    const transactions = mockTransactions[portfolioId] || []
    // Return sorted by timestamp (most recent first)
    return [...transactions].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
  },

  /**
   * Execute a trade (mock implementation)
   */
  async executeTrade(request: TradeRequest): Promise<Transaction> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    // In real implementation, this would call the API
    // For now, just return a mock success response
    const mockTransaction: Transaction = {
      id: `tx-${Date.now()}`,
      portfolioId: request.portfolioId,
      type: request.action,
      amount: 0, // Would be calculated by backend
      ticker: request.ticker,
      quantity: request.quantity,
      timestamp: new Date().toISOString(),
    }

    return mockTransaction
  },
}
