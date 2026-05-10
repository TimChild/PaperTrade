import { cn } from '@/lib/utils'

interface DataCellProps {
  /** Visual alignment. Numeric data should be `right`-aligned. */
  align?: 'left' | 'right' | 'center'
  /** Renders the value with tabular mono — use for any numeric cell. */
  numeric?: boolean
  /** Tone for delta cells (gain/loss). Otherwise leave as `neutral`. */
  tone?: 'neutral' | 'muted' | 'gain' | 'loss' | 'accent'
  /** Optional emphasis — bumps weight + ink. Use for the row's "primary" cell. */
  emphasis?: 'primary' | 'secondary'
  /** Hides the cell on screens narrower than `sm`. */
  hideOnMobile?: boolean
  /** Hides the cell on screens narrower than `md`. */
  hideUntilMd?: boolean
  className?: string
  children: React.ReactNode
  /** Optional data-testid for stable test selection. */
  testId?: string
  /**
   * Optional cell-level click handler. Useful for cells that should
   * propagate to a row click (the navigation cells) or, with
   * `e.stopPropagation()`, for cells that need to absorb the event so
   * the row click does not fire (the checkbox / actions columns).
   */
  onClick?: (e: React.MouseEvent<HTMLTableCellElement>) => void
}

interface DataRowProps {
  className?: string
  children: React.ReactNode
  /** Optional data-testid (typically per row, e.g. holding-row-AAPL). */
  testId?: string
  /** If true, the row will respond to hover with a subtle backplate. */
  interactive?: boolean
  /**
   * Optional row-level click handler. When provided, the `<tr>` becomes
   * keyboard-focusable and clickable; pair with `interactive` for the
   * hover backplate.
   */
  onClick?: (e: React.MouseEvent<HTMLTableRowElement>) => void
}

interface DataTableProps {
  /** Optional caption above the table (e.g. for screen readers). */
  caption?: React.ReactNode
  className?: string
  children: React.ReactNode
  /** Stable testid. */
  testId?: string
}

interface DataTableHeaderProps {
  className?: string
  children: React.ReactNode
}

interface DataHeaderCellProps {
  align?: 'left' | 'right' | 'center'
  hideOnMobile?: boolean
  hideUntilMd?: boolean
  className?: string
  children: React.ReactNode
}

const ALIGN_CLASSES: Record<NonNullable<DataCellProps['align']>, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

const TONE_CLASSES: Record<NonNullable<DataCellProps['tone']>, string> = {
  neutral: 'text-ink',
  muted: 'text-ink-muted',
  gain: 'text-gain',
  loss: 'text-loss',
  accent: 'text-amber',
}

const EMPHASIS_CLASSES: Record<
  NonNullable<DataCellProps['emphasis']>,
  string
> = {
  primary: 'text-ink font-medium',
  secondary: 'text-ink-muted',
}

/**
 * `<DataTable>` — wrapper for a tabular dataset. Hairline divider on
 * every row instead of zebra stripes. Designed to breathe.
 */
export function DataTable({
  caption,
  className,
  children,
  testId,
}: DataTableProps): React.JSX.Element {
  return (
    <div className={cn('overflow-x-auto -mx-4 sm:mx-0', className)}>
      <div className="inline-block min-w-full align-middle">
        <table
          className="min-w-full border-collapse"
          data-testid={testId ?? 'data-table'}
        >
          {caption ? <caption className="sr-only">{caption}</caption> : null}
          {children}
        </table>
      </div>
    </div>
  )
}

/**
 * `<DataTableHead>` — column header row. Renders eyebrow-style labels
 * (small caps + tracking) over a single hairline rule.
 */
export function DataTableHead({
  className,
  children,
}: DataTableHeaderProps): React.JSX.Element {
  return (
    <thead className={cn('border-b border-hairline', className)}>
      <tr>{children}</tr>
    </thead>
  )
}

export function DataHeaderCell({
  align = 'left',
  hideOnMobile = false,
  hideUntilMd = false,
  className,
  children,
}: DataHeaderCellProps): React.JSX.Element {
  return (
    <th
      scope="col"
      className={cn(
        'font-eyebrow text-ink-muted px-3 sm:px-5 py-3',
        ALIGN_CLASSES[align],
        hideOnMobile && 'hidden sm:table-cell',
        hideUntilMd && 'hidden md:table-cell',
        className
      )}
    >
      {children}
    </th>
  )
}

/**
 * `<DataTableBody>` — wraps body rows. Uses hairline dividers between
 * rows for restraint.
 */
export function DataTableBody({
  className,
  children,
}: DataTableHeaderProps): React.JSX.Element {
  return (
    <tbody
      className={cn(
        'divide-y divide-hairline [&_tr:last-child]:border-b-0',
        className
      )}
    >
      {children}
    </tbody>
  )
}

/**
 * `<DataRow>` — a single table row. Renders with a subtle hover backplate
 * when `interactive` is true. Children are `<DataCell>` instances.
 */
export function DataRow({
  className,
  children,
  testId,
  interactive = false,
  onClick,
}: DataRowProps): React.JSX.Element {
  return (
    <tr
      className={cn(
        'group',
        (interactive || onClick) &&
          'transition-colors duration-quick ease-editorial hover:bg-canvas-raised/50',
        onClick && 'cursor-pointer',
        className
      )}
      data-testid={testId}
      onClick={onClick}
    >
      {children}
    </tr>
  )
}

/**
 * `<DataCell>` — single cell. Numeric cells get tabular mono automatically.
 * Pair with `align="right"` for any numeric column.
 */
export function DataCell({
  align = 'left',
  numeric = false,
  tone = 'neutral',
  emphasis,
  hideOnMobile = false,
  hideUntilMd = false,
  className,
  children,
  testId,
  onClick,
}: DataCellProps): React.JSX.Element {
  return (
    <td
      className={cn(
        'whitespace-nowrap px-3 sm:px-5 py-3.5 text-body-sm',
        ALIGN_CLASSES[align],
        emphasis ? EMPHASIS_CLASSES[emphasis] : TONE_CLASSES[tone],
        numeric && 'font-tabular',
        hideOnMobile && 'hidden sm:table-cell',
        hideUntilMd && 'hidden md:table-cell',
        className
      )}
      data-testid={testId}
      onClick={onClick}
    >
      {children}
    </td>
  )
}
