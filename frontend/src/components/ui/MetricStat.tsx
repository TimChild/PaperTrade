import { cn } from '@/lib/utils'
import { Eyebrow } from './Eyebrow'

type MetricSize = 'hero' | 'lg' | 'md' | 'sm'
type MetricTone = 'neutral' | 'accent' | 'gain' | 'loss'

interface MetricStatProps {
  /** Eyebrow / label above the value (e.g. "Total value"). */
  label: string
  /** Primary value — pre-formatted string (e.g. "$156,750.00"). */
  value: React.ReactNode
  /** Optional supporting delta (e.g. "+1.59%" with tone). */
  delta?: {
    value: React.ReactNode
    tone: 'gain' | 'loss' | 'neutral'
    /** Optional secondary delta value (e.g. percent shown alongside dollar). */
    secondary?: React.ReactNode
  }
  /** Optional caption below the value (e.g. "as of 14:23:08"). */
  caption?: React.ReactNode
  /**
   * Visual scale. `hero` is reserved for the single most important number on
   * a page — use sparingly. `lg` is the default for a card-level metric.
   */
  size?: MetricSize
  /** Tone of the primary value (rare to override; default is neutral ink). */
  tone?: MetricTone
  /** data-testid for stable test selection. */
  testId?: string
  className?: string
}

/**
 * Per-size class bundles. The `value` class drives both the *type scale*
 * (`text-display-*`) and the *optical-size axis* (`opsz-display-*`). The
 * `font-display-numeric` utility consumes the `--display-opsz` set by the
 * `opsz-display-*` class to render Fraunces with a softer stroke contrast
 * than the heading cut — see the rationale in `index.css`.
 *
 * Hero scales up at `sm:` so on phones we step the opsz too (the hero size
 * shrinks to `display-lg` on narrow viewports).
 */
const SIZE_CLASSES: Record<
  MetricSize,
  { value: string; delta: string; gap: string }
> = {
  hero: {
    value:
      'text-display-lg sm:text-display-xl opsz-display-lg sm:opsz-display-hero',
    delta: 'text-body-md sm:text-body-lg',
    gap: 'gap-2 sm:gap-3',
  },
  lg: {
    value: 'text-display-md opsz-display-md',
    delta: 'text-body-sm sm:text-body-md',
    gap: 'gap-1.5 sm:gap-2',
  },
  md: {
    value: 'text-display-sm opsz-display-sm',
    delta: 'text-body-sm',
    gap: 'gap-1.5',
  },
  sm: {
    value: 'text-2xl tracking-tightish opsz-display-sm',
    delta: 'text-body-sm',
    gap: 'gap-1',
  },
}

const TONE_CLASSES: Record<MetricTone, string> = {
  neutral: 'text-ink',
  accent: 'text-amber',
  gain: 'text-gain',
  loss: 'text-loss',
}

const DELTA_TONE_CLASSES: Record<
  NonNullable<MetricStatProps['delta']>['tone'],
  string
> = {
  gain: 'text-gain',
  loss: 'text-loss',
  neutral: 'text-ink-muted',
}

/**
 * Editorial big-number primitive. Pairs a small-caps label with a
 * display-serif numeric value, an optional muted delta, and an optional
 * caption. The numeric value uses `.font-display-numeric` (a softer cut of
 * Fraunces tuned for tabular numbers — see Phase I1 / 2026-05-10) instead
 * of the heading-weight `.font-display`; this preserves Fraunces character
 * while keeping `+24.44%` actually readable at a glance.
 *
 * Numbers always render with `tabular-nums` so they line up across stacked
 * stats.
 */
export function MetricStat({
  label,
  value,
  delta,
  caption,
  size = 'lg',
  tone = 'neutral',
  testId,
  className,
}: MetricStatProps): React.JSX.Element {
  const sizes = SIZE_CLASSES[size]

  return (
    <div
      className={cn('flex flex-col', sizes.gap, className)}
      data-testid={testId ?? 'metric-stat'}
    >
      <Eyebrow>{label}</Eyebrow>
      <div
        className={cn(
          'font-display-numeric tabular-nums',
          sizes.value,
          TONE_CLASSES[tone]
        )}
        data-testid={testId ? `${testId}-value` : 'metric-stat-value'}
      >
        {value}
      </div>
      {delta ? (
        <div
          className={cn(
            'flex flex-wrap items-baseline gap-x-2 gap-y-0.5 font-tabular',
            sizes.delta,
            DELTA_TONE_CLASSES[delta.tone]
          )}
          data-testid={testId ? `${testId}-delta` : 'metric-stat-delta'}
        >
          <span>{delta.value}</span>
          {delta.secondary ? (
            <span className="text-ink-muted">{delta.secondary}</span>
          ) : null}
        </div>
      ) : null}
      {caption ? <div className="mt-1">{caption}</div> : null}
    </div>
  )
}
