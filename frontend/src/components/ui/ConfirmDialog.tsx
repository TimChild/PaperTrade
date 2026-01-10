/**
 * Confirmation Dialog component
 * Used for destructive actions to prevent accidental operations
 */

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
  variant?: 'danger' | 'warning' | 'info'
  isLoading?: boolean
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  variant = 'info',
  isLoading = false,
}: ConfirmDialogProps): React.JSX.Element | null {
  if (!isOpen) return null

  const variantStyles = {
    danger: 'bg-red-600 hover:bg-red-700 disabled:bg-red-400',
    warning: 'bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-400',
    info: 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400',
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="confirm-dialog-backdrop"
    >
      <div
        className="mx-4 max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        data-testid="confirm-dialog"
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {message}
        </p>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-300 dark:hover:bg-gray-700"
            data-testid="confirm-dialog-cancel"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`rounded-md px-4 py-2 text-sm font-medium text-white ${variantStyles[variant]}`}
            data-testid="confirm-dialog-confirm"
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
