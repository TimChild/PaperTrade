/**
 * Wrapper component for PriceChart that allows switching between implementations
 * Toggle between Recharts and Lightweight Charts implementations
 */
import { useState } from 'react'
import { PriceChart } from './PriceChart'
import { LightweightPriceChart } from './LightweightPriceChart'
import type { TimeRange } from '@/types/price'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

interface PriceChartWrapperProps {
  ticker: string
  initialTimeRange?: TimeRange
  portfolioId?: string
  defaultImplementation?: 'recharts' | 'lightweight'
  showToggle?: boolean
}

export function PriceChartWrapper({
  ticker,
  initialTimeRange = '1M',
  portfolioId,
  defaultImplementation = 'recharts',
  showToggle = true,
}: PriceChartWrapperProps): React.JSX.Element {
  const [implementation, setImplementation] = useState<
    'recharts' | 'lightweight'
  >(defaultImplementation)

  const toggleImplementation = () => {
    setImplementation((prev) =>
      prev === 'recharts' ? 'lightweight' : 'recharts'
    )
  }

  return (
    <div className="space-y-4">
      {/* Toggle Button */}
      {showToggle && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-foreground-secondary">
              Chart Implementation:{' '}
              <span className="font-medium text-foreground">
                {implementation === 'recharts'
                  ? 'Recharts'
                  : 'TradingView Lightweight Charts'}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleImplementation}
              data-testid="chart-implementation-toggle"
            >
              Switch to{' '}
              {implementation === 'recharts'
                ? 'Lightweight Charts'
                : 'Recharts'}
            </Button>
          </div>
        </Card>
      )}

      {/* Chart Component */}
      {implementation === 'recharts' ? (
        <PriceChart
          ticker={ticker}
          initialTimeRange={initialTimeRange}
          portfolioId={portfolioId}
        />
      ) : (
        <LightweightPriceChart
          ticker={ticker}
          initialTimeRange={initialTimeRange}
          portfolioId={portfolioId}
        />
      )}
    </div>
  )
}
