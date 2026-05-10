/**
 * ActivationStatusBadge — small UI element rendering an ActivationStatus.
 *
 * Color-coded per the design rule:
 *
 * - ACTIVE  → green
 * - PAUSED  → yellow
 * - STOPPED → gray
 * - ERROR   → red
 *
 * The wrapper element carries `data-testid="activation-status-{status}"` so
 * tests can assert state without scraping classnames.
 */
import type { ActivationStatus } from '@/services/api/types'

const STATUS_LABELS: Record<ActivationStatus, string> = {
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  STOPPED: 'Stopped',
  ERROR: 'Error',
}

const STATUS_STYLES: Record<ActivationStatus, string> = {
  ACTIVE:
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  PAUSED:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  STOPPED: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  ERROR: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

interface ActivationStatusBadgeProps {
  status: ActivationStatus
  className?: string
}

export function ActivationStatusBadge({
  status,
  className = '',
}: ActivationStatusBadgeProps): React.JSX.Element {
  const label = STATUS_LABELS[status]
  return (
    <span
      data-testid={`activation-status-${status}`}
      role="status"
      aria-label={`Activation status: ${label}`}
      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[status]} ${className}`}
    >
      {label}
    </span>
  )
}
