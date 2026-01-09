import { useState } from 'react'
import type { Transaction, TransactionType } from '@/types/portfolio'
import { formatCurrency, formatDate } from '@/utils/formatters'

interface TransactionListProps {
  transactions: Transaction[]
  limit?: number
  isLoading?: boolean
  showSearch?: boolean
}

function getTransactionIcon(type: TransactionType): string {
  switch (type) {
    case 'deposit':
      return '⬇️'
    case 'withdrawal':
      return '⬆️'
    case 'buy':
      return '🛒'
    case 'sell':
      return '💰'
  }
}

function getTransactionLabel(type: TransactionType): string {
  switch (type) {
    case 'deposit':
      return 'Deposit'
    case 'withdrawal':
      return 'Withdrawal'
    case 'buy':
      return 'Buy'
    case 'sell':
      return 'Sell'
  }
}

function getTransactionColorClass(type: TransactionType): string {
  switch (type) {
    case 'deposit':
      return 'text-positive dark:text-positive-light'
    case 'withdrawal':
      return 'text-gray-700 dark:text-gray-300'
    case 'buy':
      return 'text-blue-600 dark:text-blue-400'
    case 'sell':
      return 'text-negative dark:text-negative-light'
  }
}

export function TransactionList({
  transactions,
  limit,
  isLoading = false,
  showSearch = false,
}: TransactionListProps): React.JSX.Element {
  const [searchTerm, setSearchTerm] = useState('')

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded bg-gray-300 dark:bg-gray-700"
            ></div>
          ))}
        </div>
      </div>
    )
  }

  // Filter transactions by search term
  const filteredTransactions = searchTerm
    ? transactions.filter((tx) => {
        const term = searchTerm.toLowerCase()
        return (
          tx.ticker?.toLowerCase().includes(term) ||
          tx.type.toLowerCase().includes(term) ||
          formatDate(tx.timestamp).toLowerCase().includes(term) ||
          tx.notes?.toLowerCase().includes(term)
        )
      })
    : transactions

  // Apply limit after filtering
  const displayTransactions = limit
    ? filteredTransactions.slice(0, limit)
    : filteredTransactions

  if (transactions.length === 0) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-center text-gray-600 dark:text-gray-400">
          No transactions yet
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search Box */}
      {showSearch && (
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <input
            type="text"
            placeholder="Search by ticker, type, or date..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400"
            data-testid="transaction-search-input"
          />
        </div>
      )}

      {/* Transaction List */}
      {displayTransactions.length === 0 ? (
        <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <p
            className="text-center text-gray-600 dark:text-gray-400"
            data-testid="no-search-results"
          >
            No transactions found for &quot;{searchTerm}&quot;
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-gray-300 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div
            className="divide-y divide-gray-200 dark:divide-gray-700"
            data-testid="transaction-history-table"
          >
            {displayTransactions.map((transaction, idx) => {
              const colorClass = getTransactionColorClass(transaction.type)
              const isPositive = transaction.amount > 0

              return (
                <div
                  key={transaction.id}
                  data-testid={`transaction-row-${idx}`}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <div className="flex items-start gap-3">
                    <span
                      className="text-2xl"
                      role="img"
                      aria-label={transaction.type}
                    >
                      {getTransactionIcon(transaction.type)}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <p
                          className="font-medium text-gray-900 dark:text-white"
                          data-testid={`transaction-type-${idx}`}
                        >
                          {getTransactionLabel(transaction.type)}
                        </p>
                        {transaction.ticker && (
                          <span
                            className="rounded bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                            data-testid={`transaction-symbol-${idx}`}
                          >
                            {transaction.ticker}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        <span>{formatDate(transaction.timestamp)}</span>
                        {transaction.quantity && transaction.pricePerShare && (
                          <span className="ml-2">
                            {transaction.quantity} shares @{' '}
                            {formatCurrency(transaction.pricePerShare)}
                          </span>
                        )}
                      </div>
                      {transaction.notes && (
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                          {transaction.notes}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className={`text-right ${colorClass}`}>
                    <p
                      className="text-lg font-semibold"
                      data-testid={`transaction-amount-${idx}`}
                    >
                      {isPositive ? '+' : ''}
                      {formatCurrency(Math.abs(transaction.amount))}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
