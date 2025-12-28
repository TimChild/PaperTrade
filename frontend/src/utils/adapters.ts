/**
 * Adapter functions to convert backend DTOs to frontend types
 */
import type { Portfolio, Holding, Transaction } from '@/types/portfolio'
import type { PortfolioDTO, HoldingDTO, TransactionDTO, BalanceResponse } from '@/services/api/types'

/**
 * Convert backend PortfolioDTO to frontend Portfolio type
 * Note: This requires additional data (balance, holdings) to calculate totalValue and dailyChange
 */
export function adaptPortfolio(
  dto: PortfolioDTO,
  balance: BalanceResponse | null = null
): Portfolio {
  return {
    id: dto.id,
    name: dto.name,
    userId: dto.user_id,
    cashBalance: balance ? parseFloat(balance.amount) : 0,
    totalValue: balance ? parseFloat(balance.amount) : 0, // Will be updated when holdings are included
    dailyChange: 0, // TODO: Calculate from historical data when available
    dailyChangePercent: 0, // TODO: Calculate from historical data when available
    createdAt: dto.created_at,
  }
}

/**
 * Convert backend HoldingDTO to frontend Holding type
 * Note: currentPrice is not available from backend yet (Phase 2 - market data integration)
 */
export function adaptHolding(dto: HoldingDTO): Holding {
  const quantity = parseFloat(dto.quantity)
  const costBasis = parseFloat(dto.cost_basis)
  const averageCost = dto.average_cost_per_share
    ? parseFloat(dto.average_cost_per_share)
    : costBasis / quantity

  // Mock current price until real market data is available
  // In Phase 2, this will come from Alpha Vantage API
  const currentPrice = averageCost * (1 + (Math.random() * 0.1 - 0.05)) // +/- 5% mock variance

  const marketValue = currentPrice * quantity
  const gainLoss = marketValue - costBasis
  const gainLossPercent = (gainLoss / costBasis) * 100

  return {
    ticker: dto.ticker,
    quantity,
    averageCost,
    currentPrice,
    marketValue,
    gainLoss,
    gainLossPercent,
  }
}

/**
 * Convert backend TransactionDTO to frontend Transaction type
 */
export function adaptTransaction(dto: TransactionDTO): Transaction {
  // Map backend transaction_type to frontend type
  let type: Transaction['type']
  switch (dto.transaction_type) {
    case 'DEPOSIT':
      type = 'deposit'
      break
    case 'WITHDRAWAL':
      type = 'withdrawal'
      break
    case 'BUY':
      type = 'buy'
      break
    case 'SELL':
      type = 'sell'
      break
    default:
      type = 'deposit' // fallback
  }

  return {
    id: dto.id,
    portfolioId: dto.portfolio_id,
    type,
    amount: Math.abs(parseFloat(dto.cash_change)),
    ticker: dto.ticker || undefined,
    quantity: dto.quantity ? parseFloat(dto.quantity) : undefined,
    pricePerShare: dto.price_per_share ? parseFloat(dto.price_per_share) : undefined,
    timestamp: dto.timestamp,
    notes: dto.notes || undefined,
  }
}
