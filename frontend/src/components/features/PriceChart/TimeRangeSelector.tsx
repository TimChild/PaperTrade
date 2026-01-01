/**
 * Time range selector component for price charts
 */
import type { TimeRange } from '@/types/price'

interface TimeRangeSelectorProps {
  selected: TimeRange
  onChange: (range: TimeRange) => void
}

const TIME_RANGES: TimeRange[] = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

export function TimeRangeSelector({ selected, onChange }: TimeRangeSelectorProps): React.JSX.Element {
  return (
    <div className="flex gap-1 rounded-lg border border-gray-300 bg-white p-1 dark:border-gray-700 dark:bg-gray-800">
      {TIME_RANGES.map((range) => (
        <button
          key={range}
          onClick={() => onChange(range)}
          className={`
            rounded px-3 py-1 text-sm font-medium transition-colors
            ${
              selected === range
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
            }
          `}
          aria-label={`Show ${range} price history`}
          aria-pressed={selected === range}
        >
          {range}
        </button>
      ))}
    </div>
  )
}
