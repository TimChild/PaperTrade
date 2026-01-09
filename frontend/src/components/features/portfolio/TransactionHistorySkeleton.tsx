/**
 * Skeleton loader for transaction history
 * Displays while transaction data is being fetched
 */

export function TransactionHistorySkeleton(): React.JSX.Element {
  return (
    <div
      className="rounded-lg border border-gray-300 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800"
      data-testid="transaction-history-skeleton"
    >
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center justify-between p-4">
            <div className="flex items-start gap-3">
              {/* Icon placeholder */}
              <div className="h-6 w-6 rounded-full bg-gray-300 dark:bg-gray-700"></div>

              <div className="space-y-2">
                {/* Transaction type and ticker */}
                <div className="flex items-center gap-2">
                  <div className="h-5 w-20 rounded bg-gray-300 dark:bg-gray-700"></div>
                  <div className="h-4 w-12 rounded bg-gray-300 dark:bg-gray-700"></div>
                </div>

                {/* Date and details */}
                <div className="h-4 w-48 rounded bg-gray-200 dark:bg-gray-600"></div>
              </div>
            </div>

            {/* Amount */}
            <div className="h-6 w-24 rounded bg-gray-300 dark:bg-gray-700"></div>
          </div>
        ))}
      </div>
    </div>
  )
}
