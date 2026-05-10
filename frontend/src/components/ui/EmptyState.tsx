/**
 * Editorial empty state — eyebrow + serif heading + optional supporting copy
 * + restrained amber CTA. Replaces the cute legacy "centered gray text +
 * button" empty state with a measured editorial moment.
 *
 * Usage prefers the explicit `eyebrow` / `title` / `description` triplet, but
 * the legacy `message` prop is still accepted (rendered as the title) for
 * backward compatibility with the few call sites that haven't migrated yet.
 */
import { Eyebrow } from './Eyebrow'

interface EmptyStateProps {
  /** Small-caps tracked label above the heading. Defaults to "Nothing here yet". */
  eyebrow?: string
  /** Editorial display heading — the lead line of the empty state. */
  title?: string
  /** Optional one-line supporting copy below the title. */
  description?: React.ReactNode
  /** Optional CTA, typically an amber `<Button>`. */
  action?: React.ReactNode
  /** Legacy single-string message (treated as the title). */
  message?: string
  /** Legacy icon — rarely used in editorial mode; rendered above the eyebrow. */
  icon?: React.ReactNode
  className?: string
}

export function EmptyState({
  eyebrow = 'Nothing here yet',
  title,
  description,
  action,
  message,
  icon,
  className = '',
}: EmptyStateProps): React.JSX.Element {
  const heading = title ?? message ?? 'No results'

  return (
    <div
      className={`flex flex-col items-center justify-center gap-4 py-16 text-center ${className}`}
      data-testid="empty-state"
    >
      {icon && <div className="text-ink-faint">{icon}</div>}
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="font-display text-display-sm sm:text-display-md text-ink max-w-xl">
        {heading}
      </h2>
      {description && (
        <p className="text-body-sm text-ink-muted max-w-prose">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
