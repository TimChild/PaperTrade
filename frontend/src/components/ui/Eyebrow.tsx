import { cn } from '@/lib/utils'

interface EyebrowProps extends React.HTMLAttributes<HTMLSpanElement> {
  /**
   * Tone of the eyebrow. `accent` colors it amber for emphasis (use sparingly,
   * only when the eyebrow itself is the load-bearing label — e.g. "Updated"
   * next to a live timestamp). Default is `muted`.
   */
  tone?: 'muted' | 'accent'
  className?: string
  children: React.ReactNode
}

/**
 * Editorial small-caps label that pairs above (or alongside) display-font
 * headings. Renders as a `<span>` by default — semantic upgrade is up to
 * the caller.
 */
export function Eyebrow({
  tone = 'muted',
  className,
  children,
  ...rest
}: EyebrowProps): React.JSX.Element {
  return (
    <span
      className={cn(
        'font-eyebrow inline-block',
        tone === 'accent' ? 'text-amber' : 'text-ink-muted',
        className
      )}
      data-testid="eyebrow"
      {...rest}
    >
      {children}
    </span>
  )
}
