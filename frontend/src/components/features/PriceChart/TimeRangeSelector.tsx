/**
 * Time range selector component for price charts.
 *
 * Editorial pill: hairline-bordered rail with selected segment in amber. No
 * solid blue, no rounded-large pills. Subtle hover on inactive segments.
 */
import type { TimeRange } from '@/types/price'

interface TimeRangeSelectorProps {
  selected: TimeRange
  onChange: (range: TimeRange) => void
}

const TIME_RANGES: TimeRange[] = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

export function TimeRangeSelector({
  selected,
  onChange,
}: TimeRangeSelectorProps): React.JSX.Element {
  return (
    <div
      role="group"
      aria-label="Select time range"
      className="inline-flex rounded-editorial border border-hairline bg-canvas-sunken/40 p-0.5"
    >
      {TIME_RANGES.map((range) => {
        const isSelected = selected === range
        return (
          <button
            key={range}
            type="button"
            onClick={() => onChange(range)}
            className={`
              relative px-2.5 py-1 text-xs font-eyebrow rounded-[3px]
              transition-colors duration-quick ease-editorial
              ${
                isSelected
                  ? 'bg-canvas-raised text-amber'
                  : 'text-ink-subtle hover:text-ink'
              }
            `}
            style={{ minHeight: 'auto', letterSpacing: '0.12em' }}
            aria-label={`Show ${range} price history`}
            aria-pressed={isSelected}
            data-testid={`time-range-${range}`}
          >
            {range}
          </button>
        )
      })}
    </div>
  )
}
