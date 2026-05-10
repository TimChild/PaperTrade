import { cn } from '@/lib/utils'
import { Eyebrow } from './Eyebrow'

interface SectionHeaderProps {
  /** Section title — rendered with the editorial display serif. */
  title: string
  /** Optional eyebrow above the title (small caps). */
  eyebrow?: string
  /** Optional supporting copy below the title (one-line summary, etc.). */
  description?: React.ReactNode
  /** Optional content (link, button, etc.) on the right of the header row. */
  trailing?: React.ReactNode
  /** If true, renders a hairline rule under the header. */
  withRule?: boolean
  /** HTML heading level (defaults to h2). */
  as?: 'h1' | 'h2' | 'h3'
  /** Size of the heading text. */
  size?: 'sm' | 'md'
  className?: string
}

/**
 * Editorial section header — eyebrow + display-serif heading + optional
 * description + optional trailing element + optional hairline rule.
 *
 * Used to introduce sections within a page. Distinct from the page hero
 * (which is rendered ad-hoc since the hero is the strongest moment on
 * each page and benefits from per-page composition).
 */
export function SectionHeader({
  title,
  eyebrow,
  description,
  trailing,
  withRule = false,
  as: Heading = 'h2',
  size = 'md',
  className,
}: SectionHeaderProps): React.JSX.Element {
  const sizeClass =
    size === 'sm' ? 'text-display-sm' : 'text-display-md sm:text-display-md'

  return (
    <header
      className={cn(
        'mb-4 sm:mb-5',
        withRule && 'pb-3 border-b border-hairline',
        className
      )}
      data-testid="section-header"
    >
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
        <div className="space-y-1.5">
          {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
          <Heading
            className={cn('font-display text-ink', sizeClass)}
            data-testid="section-header-title"
          >
            {title}
          </Heading>
          {description ? (
            <p className="text-body-sm text-ink-muted max-w-prose">
              {description}
            </p>
          ) : null}
        </div>
        {trailing ? (
          <div className="flex-shrink-0" data-testid="section-header-trailing">
            {trailing}
          </div>
        ) : null}
      </div>
    </header>
  )
}
