/**
 * TypeScript types matching backend API DTOs
 * These types mirror the FastAPI Pydantic models
 */

// Portfolio types
export interface PortfolioDTO {
  id: string
  user_id: string
  name: string
  created_at: string // ISO 8601
}

export interface CreatePortfolioRequest {
  name: string
  initial_deposit: string // Decimal as string
  currency?: string
}

export interface CreatePortfolioResponse {
  portfolio_id: string
  transaction_id: string
}

// Transaction types
export interface TransactionDTO {
  id: string
  portfolio_id: string
  transaction_type: 'DEPOSIT' | 'WITHDRAWAL' | 'BUY' | 'SELL'
  timestamp: string // ISO 8601
  cash_change: string // Decimal as string
  ticker?: string | null
  quantity?: string | null // Decimal as string
  price_per_share?: string | null // Decimal as string
  notes?: string | null
}

export interface TransactionListResponse {
  transactions: TransactionDTO[]
  total_count: number
  limit: number
  offset: number
}

// Cash operation types
export interface DepositRequest {
  amount: string // Decimal as string
  currency?: string
}

export interface WithdrawRequest {
  amount: string // Decimal as string
  currency?: string
}

export interface TransactionResponse {
  transaction_id: string
}

// Trade types
export interface TradeRequest {
  action: 'BUY' | 'SELL'
  ticker: string
  quantity: string // Decimal as string
  as_of?: string // Optional ISO 8601 timestamp for backtesting
}

// Balance types
export interface BalanceResponse {
  amount: string // Decimal as string
  currency: string
  as_of: string // ISO 8601 timestamp
}

// Holdings types
export interface HoldingDTO {
  ticker: string
  quantity: string // Decimal as string
  cost_basis: string // Decimal as string
  average_cost_per_share: string | null // Decimal as string
}

export interface HoldingsResponse {
  holdings: HoldingDTO[]
}

// Error response
export interface ErrorResponse {
  detail: string
}
