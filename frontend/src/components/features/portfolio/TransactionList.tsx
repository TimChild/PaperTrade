import type { Transaction, TransactionType } from '@/types/portfolio'
import { formatCurrency, formatDate } from '@/utils/formatters'

interface TransactionListProps {
  transactions: Transaction[]
  limit?: number
  isLoading?: boolean
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
}: TransactionListProps): React.JSX.Element {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded bg-gray-300 dark:bg-gray-700"></div>
          ))}
        </div>
      </div>
    )
  }

  const displayTransactions = limit ? transactions.slice(0, limit) : transactions

  if (displayTransactions.length === 0) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-center text-gray-600 dark:text-gray-400">
          No transactions yet
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-300 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {displayTransactions.map((transaction) => {
          const colorClass = getTransactionColorClass(transaction.type)
          const isPositive = transaction.amount > 0

          return (
            <div
              key={transaction.id}
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl" role="img" aria-label={transaction.type}>
                  {getTransactionIcon(transaction.type)}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {getTransactionLabel(transaction.type)}
                    </p>
                    {transaction.ticker && (
                      <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                        {transaction.ticker}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    <span>{formatDate(transaction.timestamp)}</span>
                    {transaction.quantity && transaction.pricePerShare && (
                      <span className="ml-2">
                        {transaction.quantity} shares @ {formatCurrency(transaction.pricePerShare)}
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
                <p className="text-lg font-semibold">
                  {isPositive ? '+' : ''}
                  {formatCurrency(Math.abs(transaction.amount))}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
