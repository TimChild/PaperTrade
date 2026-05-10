/**
 * Editorial confirmation dialog — canvas-raised panel with hairline border,
 * eyebrow + serif heading, body copy, and a button row that swaps tone with
 * the confirm `variant`.
 *
 * - `danger`   → loss-tone confirm (uses the destructive Button variant).
 * - `warning`  → amber-leaning confirm (uses the default Button variant —
 *                amber on canvas).
 * - `info`     → amber confirm (default Button).
 */
import { Eyebrow } from './Eyebrow'
import { Button } from './button'

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

const VARIANT_EYEBROW: Record<
  NonNullable<ConfirmDialogProps['variant']>,
  string
> = {
  danger: 'Confirm action',
  warning: 'Heads up',
  info: 'Confirm',
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

  const confirmVariant = variant === 'danger' ? 'destructive' : 'default'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-canvas-sunken/80 backdrop-blur-sm"
      data-testid="confirm-dialog-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) onCancel()
      }}
    >
      <div
        className="mx-4 max-w-md rounded-editorial border border-hairline bg-canvas-raised p-6 shadow-elevated"
        data-testid="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
      >
        <Eyebrow>{VARIANT_EYEBROW[variant]}</Eyebrow>
        <h3
          id="confirm-dialog-title"
          className="mt-2 font-display text-display-sm tracking-tight text-ink"
        >
          {title}
        </h3>
        <p className="mt-3 text-body-sm text-ink-muted">{message}</p>

        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="ghost"
            onClick={onCancel}
            disabled={isLoading}
            data-testid="confirm-dialog-cancel"
          >
            Cancel
          </Button>
          <Button
            variant={confirmVariant}
            onClick={onConfirm}
            disabled={isLoading}
            data-testid="confirm-dialog-confirm"
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
