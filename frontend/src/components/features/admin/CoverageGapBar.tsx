/**
 * CoverageGapBar — inline SVG mini-viz for the admin data-coverage table.
 *
 * Renders a 120×16px strip showing:
 * - A neutral-700 background band for the covered range
 *   (`coverage_start` → `coverage_end`).
 * - Red-500 stripes for each gap range, positioned proportionally
 *   within the covered band.
 * - A native SVG `<title>` for accessible hover tooltips listing gap
 *   dates (e.g. "Apr 12, 2026" or "May 15–17, 2026").
 *
 * Empty state: when `gapRanges.length === 0`, renders the solid
 * neutral band only (no stripes).
 *
 * No-coverage state: when `coverageStart`/`coverageEnd` is `null`,
 * renders nothing — consistent with the gap-count cell's behaviour.
 *
 * Task #222.
 */

import type { GapRange } from '@/services/api/types'

/** Width of the rendered SVG in pixels. */
const BAR_WIDTH = 120
/** Height of the rendered SVG in pixels. */
const BAR_HEIGHT = 16
/** Vertical padding that keeps the band centred in the viewBox. */
const BAND_Y = 4
/** Height of the coverage band within the viewBox. */
const BAND_HEIGHT = BAR_HEIGHT - BAND_Y * 2

interface CoverageGapBarProps {
  coverageStart: string | null
  coverageEnd: string | null
  gapRanges: Array<GapRange>
}

/**
 * Format a gap range as a human-readable string for the tooltip.
 *
 * Single-day gaps: "Apr 12, 2026"
 * Multi-day gaps:  "May 15–17, 2026" (same month) or
 *                  "Dec 28, 2025 – Jan 3, 2026" (cross-month)
 */
function formatGapLabel(gap: GapRange): string {
  const fmt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    // Treat as local date — the strings are YYYY-MM-DD without a time
    // component, so parsing as UTC and displaying in UTC avoids the
    // "off by one day" issue caused by local-timezone offsets.
    timeZone: 'UTC',
  })

  if (gap.start === gap.end) {
    return fmt.format(new Date(gap.start + 'T00:00:00Z'))
  }

  const startDate = new Date(gap.start + 'T00:00:00Z')
  const endDate = new Date(gap.end + 'T00:00:00Z')

  // Same month + year: "May 15–17, 2026"
  if (
    startDate.getUTCMonth() === endDate.getUTCMonth() &&
    startDate.getUTCFullYear() === endDate.getUTCFullYear()
  ) {
    const month = startDate.toLocaleString('en-US', {
      month: 'short',
      timeZone: 'UTC',
    })
    const year = startDate.getUTCFullYear()
    return `${month} ${startDate.getUTCDate()}–${endDate.getUTCDate()}, ${year}`
  }

  // Cross-month: full dates for both ends
  const startFmt = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
  return `${startFmt.format(startDate)} – ${startFmt.format(endDate)}`
}

/**
 * Map an ISO date string to its timestamp in ms (UTC midnight).
 */
function toMs(isoDate: string): number {
  return new Date(isoDate + 'T00:00:00Z').getTime()
}

export function CoverageGapBar({
  coverageStart,
  coverageEnd,
  gapRanges,
}: CoverageGapBarProps): React.JSX.Element | null {
  // No-coverage state — render nothing.
  if (coverageStart === null || coverageEnd === null) {
    return null
  }

  const startMs = toMs(coverageStart)
  const endMs = toMs(coverageEnd)
  const spanMs = endMs - startMs

  // If the span is zero (single-day coverage) treat the whole bar as
  // covered and render no gaps regardless of gapRanges content.
  const zeroSpan = spanMs <= 0

  /**
   * Convert a date string to an x-position within the SVG band.
   * Clamps the result to [0, BAR_WIDTH].
   */
  function dateToX(isoDate: string): number {
    if (zeroSpan) return 0
    const ms = toMs(isoDate)
    const ratio = (ms - startMs) / spanMs
    return Math.max(0, Math.min(BAR_WIDTH, ratio * BAR_WIDTH))
  }

  const tooltipLines =
    gapRanges.length > 0 ? gapRanges.map(formatGapLabel).join('\n') : undefined

  return (
    <svg
      width={BAR_WIDTH}
      height={BAR_HEIGHT}
      viewBox={`0 0 ${BAR_WIDTH} ${BAR_HEIGHT}`}
      aria-label={
        gapRanges.length > 0
          ? `Coverage gaps: ${tooltipLines}`
          : 'Full coverage — no gaps'
      }
      data-testid="coverage-gap-bar"
      role="img"
    >
      {tooltipLines !== undefined && <title>{tooltipLines}</title>}

      {/* Covered-range background band */}
      <rect
        x={0}
        y={BAND_Y}
        width={BAR_WIDTH}
        height={BAND_HEIGHT}
        rx={2}
        className="fill-neutral-700"
        data-testid="coverage-gap-bar-band"
      />

      {/* Gap stripes */}
      {!zeroSpan &&
        gapRanges.map((gap, index) => {
          const x = dateToX(gap.start)
          const x2 = dateToX(gap.end)
          // Give single-day gaps a minimum 2px width for visibility.
          const width = Math.max(2, x2 - x)
          return (
            <rect
              key={index}
              x={x}
              y={BAND_Y}
              width={width}
              height={BAND_HEIGHT}
              className="fill-loss"
              data-testid={`coverage-gap-bar-gap-${index}`}
            />
          )
        })}
    </svg>
  )
}
