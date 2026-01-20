import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TransactionList } from './TransactionList'
import type { Transaction } from '@/types/portfolio'

describe('TransactionList', () => {
  const mockTransactions: Transaction[] = [
    {
      id: '1',
      portfolioId: 'portfolio-1',
      type: 'buy',
      amount: 1000,
      ticker: 'AAPL',
      quantity: 10,
      pricePerShare: 100,
      timestamp: '2024-01-15T10:00:00Z',
    },
    {
      id: '2',
      portfolioId: 'portfolio-1',
      type: 'deposit',
      amount: 5000,
      timestamp: '2024-01-14T10:00:00Z',
    },
    {
      id: '3',
      portfolioId: 'portfolio-1',
      type: 'sell',
      amount: 500,
      ticker: 'MSFT',
      quantity: 5,
      pricePerShare: 100,
      timestamp: '2024-01-13T10:00:00Z',
    },
  ]

  describe('rendering', () => {
    it('should render transaction list', () => {
      render(<TransactionList transactions={mockTransactions} />)

      expect(screen.getByTestId('transaction-history-table')).toBeInTheDocument()
      expect(screen.getAllByTestId(/transaction-row-/)).toHaveLength(3)
    })

    it('should render empty state when no transactions', () => {
      render(<TransactionList transactions={[]} />)

      expect(screen.getByText('No transactions yet')).toBeInTheDocument()
    })

    it('should render loading skeleton when loading', () => {
      render(<TransactionList transactions={[]} isLoading={true} />)

      // Skeleton should render 3 placeholder items (just check they're present)
      const skeletons = document.querySelectorAll('.animate-pulse')
      expect(skeletons).toHaveLength(3)
    })
  })

  describe('highlight behavior', () => {
    it('should apply highlight class to new transactions', () => {
      const transactionsWithNew: Transaction[] = [
        { ...mockTransactions[0], isNew: true },
        mockTransactions[1],
        mockTransactions[2],
      ]

      render(<TransactionList transactions={transactionsWithNew} />)

      const rows = screen.getAllByTestId(/transaction-row-/)
      expect(rows[0]).toHaveClass('highlight-new')
      expect(rows[1]).not.toHaveClass('highlight-new')
      expect(rows[2]).not.toHaveClass('highlight-new')
    })

    it('should not apply highlight class to transactions without isNew flag', () => {
      render(<TransactionList transactions={mockTransactions} />)

      const rows = screen.getAllByTestId(/transaction-row-/)
      rows.forEach((row) => {
        expect(row).not.toHaveClass('highlight-new')
      })
    })

    it('should add aria-label to new transactions', () => {
      const transactionsWithNew: Transaction[] = [
        { ...mockTransactions[0], isNew: true },
        mockTransactions[1],
      ]

      render(<TransactionList transactions={transactionsWithNew} />)

      const firstRow = screen.getByTestId('transaction-row-0')
      expect(firstRow).toHaveAttribute('aria-label', 'New transaction added')

      const secondRow = screen.getByTestId('transaction-row-1')
      expect(secondRow).not.toHaveAttribute('aria-label')
    })

    it('should have aria-live attribute on transaction container', () => {
      render(<TransactionList transactions={mockTransactions} />)

      const container = screen.getByTestId('transaction-history-table')
      expect(container).toHaveAttribute('aria-live', 'polite')
      expect(container).toHaveAttribute('aria-relevant', 'additions')
    })
  })

  describe('search functionality', () => {
    it('should show search input when showSearch is true', () => {
      render(<TransactionList transactions={mockTransactions} showSearch={true} />)

      expect(screen.getByTestId('transaction-search-input')).toBeInTheDocument()
    })

    it('should not show search input when showSearch is false', () => {
      render(<TransactionList transactions={mockTransactions} showSearch={false} />)

      expect(screen.queryByTestId('transaction-search-input')).not.toBeInTheDocument()
    })
  })

  describe('transaction details', () => {
    it('should display transaction type', () => {
      render(<TransactionList transactions={mockTransactions} />)

      expect(screen.getByTestId('transaction-type-0')).toHaveTextContent('Buy')
      expect(screen.getByTestId('transaction-type-1')).toHaveTextContent('Deposit')
      expect(screen.getByTestId('transaction-type-2')).toHaveTextContent('Sell')
    })

    it('should display ticker for trade transactions', () => {
      render(<TransactionList transactions={mockTransactions} />)

      expect(screen.getByTestId('transaction-symbol-0')).toHaveTextContent('AAPL')
      expect(screen.getByTestId('transaction-symbol-2')).toHaveTextContent('MSFT')
    })

    it('should display transaction amount', () => {
      render(<TransactionList transactions={mockTransactions} />)

      expect(screen.getByTestId('transaction-amount-0')).toHaveTextContent('$1,000.00')
      expect(screen.getByTestId('transaction-amount-1')).toHaveTextContent('+$5,000.00')
      expect(screen.getByTestId('transaction-amount-2')).toHaveTextContent('$500.00')
    })
  })
})
