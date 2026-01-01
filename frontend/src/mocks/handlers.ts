/**
 * Mock Service Worker (MSW) handlers for testing
 * These handlers intercept HTTP requests during tests and return mock responses
 */
import { http, HttpResponse } from 'msw'

const API_BASE_URL = 'http://localhost:8000/api/v1'

// Mock data matching backend DTOs
const mockPortfolio = {
  id: '00000000-0000-0000-0000-000000000001',
  user_id: '00000000-0000-0000-0000-000000000001',
  name: 'Test Portfolio',
  created_at: '2024-01-01T00:00:00Z',
}

const mockBalance = {
  amount: '10000.00',
  currency: 'USD',
  as_of: '2024-01-01T00:00:00Z',
}

const mockHoldings = {
  holdings: [
    {
      ticker: 'AAPL',
      quantity: '10.00',
      cost_basis: '1500.00',
      average_cost_per_share: '150.00',
    },
  ],
}

const mockTransactions = {
  transactions: [
    {
      id: '00000000-0000-0000-0000-000000000002',
      portfolio_id: '00000000-0000-0000-0000-000000000001',
      transaction_type: 'DEPOSIT',
      timestamp: '2024-01-01T00:00:00Z',
      cash_change: '10000.00',
      ticker: null,
      quantity: null,
      price_per_share: null,
      notes: 'Initial deposit',
    },
  ],
  total_count: 1,
  limit: 50,
  offset: 0,
}

// API handlers
export const handlers = [
  // List portfolios
  http.get(`${API_BASE_URL}/portfolios`, () => {
    return HttpResponse.json([mockPortfolio])
  }),

  // Get portfolio by ID
  http.get(`${API_BASE_URL}/portfolios/:id`, () => {
    return HttpResponse.json(mockPortfolio)
  }),

  // Get portfolio balance
  http.get(`${API_BASE_URL}/portfolios/:id/balance`, () => {
    return HttpResponse.json(mockBalance)
  }),

  // Get portfolio holdings
  http.get(`${API_BASE_URL}/portfolios/:id/holdings`, () => {
    return HttpResponse.json(mockHoldings)
  }),

  // Get portfolio transactions
  http.get(`${API_BASE_URL}/portfolios/:id/transactions`, () => {
    return HttpResponse.json(mockTransactions)
  }),

  // Create portfolio
  http.post(`${API_BASE_URL}/portfolios`, async () => {
    return HttpResponse.json({
      portfolio_id: '00000000-0000-0000-0000-000000000001',
      transaction_id: '00000000-0000-0000-0000-000000000002',
    })
  }),

  // Deposit cash
  http.post(`${API_BASE_URL}/portfolios/:id/deposit`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000003',
    })
  }),

  // Withdraw cash
  http.post(`${API_BASE_URL}/portfolios/:id/withdraw`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000004',
    })
  }),

  // Execute trade
  http.post(`${API_BASE_URL}/portfolios/:id/trades`, () => {
    return HttpResponse.json({
      transaction_id: '00000000-0000-0000-0000-000000000005',
    })
  }),

  // Get current price for a ticker
  http.get(`${API_BASE_URL}/prices/:ticker`, ({ params }) => {
    const { ticker } = params

    // Mock prices for common stocks
    const mockPrices: Record<string, number> = {
      AAPL: 192.53,
      GOOGL: 140.93,
      MSFT: 374.58,
      TSLA: 248.48,
      AMZN: 178.25,
      NVDA: 495.22,
      META: 338.54,
      BRK: 348.45,
      V: 272.31,
      JPM: 153.72,
    }

    const price = mockPrices[ticker as string]
    if (!price) {
      return HttpResponse.json(
        { detail: `Ticker ${ticker} not found` },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      ticker: { symbol: ticker },
      price: { amount: price, currency: 'USD' },
      timestamp: new Date().toISOString(),
      source: 'database',
      interval: 'real-time',
    })
  }),

  // Get price history for a ticker
  http.get(`${API_BASE_URL}/prices/:ticker/history`, ({ params, request }) => {
    const { ticker } = params
    const url = new URL(request.url)
    const start = url.searchParams.get('start')
    const end = url.searchParams.get('end')

    // Mock prices for common stocks
    const mockPrices: Record<string, number> = {
      AAPL: 192.53,
      GOOGL: 140.93,
      MSFT: 374.58,
      TSLA: 248.48,
      AMZN: 178.25,
      NVDA: 495.22,
      META: 338.54,
      BRK: 348.45,
      V: 272.31,
      JPM: 153.72,
    }

    const basePrice = mockPrices[ticker as string]
    if (!basePrice) {
      return HttpResponse.json(
        { detail: `Ticker ${ticker} not found` },
        { status: 404 }
      )
    }

    // Generate mock price history data
    const startDate = start ? new Date(start) : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    const endDate = end ? new Date(end) : new Date()
    const dataPoints: Array<{
      ticker: { symbol: string }
      price: { amount: number; currency: string }
      timestamp: string
      source: string
      interval: string
    }> = []

    const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (24 * 60 * 60 * 1000))
    const numPoints = Math.min(daysDiff, 100) // Limit to 100 points

    for (let i = 0; i < numPoints; i++) {
      const date = new Date(startDate.getTime() + (i * (endDate.getTime() - startDate.getTime())) / numPoints)
      // Add some variance to the price (±5%)
      const variance = (Math.random() - 0.5) * 0.1 * basePrice
      const price = basePrice + variance

      dataPoints.push({
        ticker: { symbol: ticker as string },
        price: { amount: parseFloat(price.toFixed(2)), currency: 'USD' },
        timestamp: date.toISOString(),
        source: 'database',
        interval: '1day',
      })
    }

    return HttpResponse.json({
      data: dataPoints,
      ticker: { symbol: ticker },
      start: startDate.toISOString(),
      end: endDate.toISOString(),
      interval: '1day',
    })
  }),
]
