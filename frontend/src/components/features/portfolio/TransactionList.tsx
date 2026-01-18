import { useState } from 'react'
import type { Transaction, TransactionType } from '@/types/portfolio'
import { formatCurrency, formatDate } from '@/utils/formatters'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

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
      return 'text-positive'
    case 'withdrawal':
      return 'text-foreground-secondary'
    case 'buy':
      return 'text-primary'
    case 'sell':
      return 'text-negative'
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
      <Card>
        <CardContent className="space-y-3 pt-6">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </CardContent>
      </Card>
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
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-foreground-secondary">
            No transactions yet
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3 sm:space-y-4">
      {/* Search Box */}
      {showSearch && (
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <svg
              className="h-4 w-4 sm:h-5 sm:w-5 text-foreground-tertiary"
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
          <Input
            type="text"
            placeholder="Search by ticker, type, or date..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 sm:pl-10 text-sm sm:text-base"
            data-testid="transaction-search-input"
          />
        </div>
      )}

      {/* Transaction List */}
      {displayTransactions.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p
              className="text-center text-foreground-secondary text-sm sm:text-base"
              data-testid="no-search-results"
            >
              No transactions found for &quot;{searchTerm}&quot;
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
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
                    className="flex items-center justify-between p-3 sm:p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-start gap-2 sm:gap-3 flex-1 min-w-0">
                      <span
                        className="text-xl sm:text-2xl flex-shrink-0"
                        role="img"
                        aria-label={transaction.type}
                      >
                        {getTransactionIcon(transaction.type)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p
                            className="font-medium text-foreground-primary text-sm sm:text-base"
                            data-testid={`transaction-type-${idx}`}
                          >
                            {getTransactionLabel(transaction.type)}
                          </p>
                          {transaction.ticker && (
                            <Badge
                              variant="secondary"
                              data-testid={`transaction-symbol-${idx}`}
                              className="text-xs"
                            >
                              {transaction.ticker}
                            </Badge>
                          )}
                        </div>
                        <div className="mt-1 text-xs sm:text-sm text-foreground-secondary">
                          <span>{formatDate(transaction.timestamp)}</span>
                          {transaction.quantity &&
                            transaction.pricePerShare && (
                              <span className="ml-2">
                                {transaction.quantity} shares @{' '}
                                {formatCurrency(transaction.pricePerShare)}
                              </span>
                            )}
                        </div>
                        {transaction.notes && (
                          <p className="mt-1 text-xs text-foreground-tertiary truncate">
                            {transaction.notes}
                          </p>
                        )}
                      </div>
                    </div>
                    <div
                      className={`text-right flex-shrink-0 ml-2 ${colorClass}`}
                    >
                      <p
                        className="text-base sm:text-lg font-semibold"
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
