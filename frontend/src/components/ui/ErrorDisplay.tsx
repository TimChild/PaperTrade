/**
 * Editorial error display — restrained loss-tone hairline panel with an
 * eyebrow ("Error") and the formatted error message. No bright red splash —
 * the loss tone is muted brick to keep with the editorial mood.
 */
import { AxiosError } from 'axios'
import type { ErrorResponse } from '@/services/api/types'
import { formatTradeError } from '@/utils/errorFormatters'
import { Eyebrow } from './Eyebrow'

interface ErrorDisplayProps {
  error: Error | AxiosError<ErrorResponse> | null
  className?: string
}

export function ErrorDisplay({
  error,
  className = '',
}: ErrorDisplayProps): React.JSX.Element | null {
  if (!error) return null

  const message = formatTradeError(error)

  return (
    <div
      className={`rounded-editorial border border-hairline bg-loss-soft/40 p-4 ${className}`}
      role="alert"
      data-testid="error-display"
    >
      <Eyebrow tone="accent" className="text-loss">
        Error
      </Eyebrow>
      <p className="mt-2 text-body-sm text-ink">{message}</p>
    </div>
  )
}
