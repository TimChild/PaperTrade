// Portfolio domain types

export interface Portfolio {
  id: string
  name: string
  userId: string
  cashBalance: number
  totalValue: number
  dailyChange: number
  dailyChangePercent: number
  createdAt: string
}

export interface Holding {
  ticker: string
  quantity: number
  averageCost: number
  currentPrice: number
  marketValue: number
  gainLoss: number
  gainLossPercent: number
}

export type TransactionType = 'deposit' | 'withdrawal' | 'buy' | 'sell'

export interface Transaction {
  id: string
  portfolioId: string
  type: TransactionType
  amount: number
  ticker?: string
  quantity?: number
  pricePerShare?: number
  timestamp: string
  notes?: string
  isNew?: boolean // Flag for highlighting new transactions
}

export interface TradeRequest {
  portfolioId: string
  action: 'buy' | 'sell'
  ticker: string
  quantity: number
}
