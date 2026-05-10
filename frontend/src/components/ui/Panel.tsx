import * as React from 'react'
import { cn } from '@/lib/utils'

interface PanelProps extends React.HTMLAttributes<HTMLElement> {
  /**
   * Visual elevation. Editorial surfaces lean flat — `flush` is the
   * default and renders the panel as a hairline-bordered region against
   * the canvas (no shadow, no rounded corners that scream "card"). Use
   * `raised` only when the panel needs to register as a distinct
   * floating object.
   */
  variant?: 'flush' | 'raised'
  /**
   * If true, omits the inner padding so callers can render edge-to-edge
   * (e.g. a table that should bleed to the panel border).
   */
  unpadded?: boolean
  className?: string
  children: React.ReactNode
  as?: 'section' | 'div' | 'article'
}

/**
 * Editorial surface primitive. Replaces the default shadcn-style "card with
 * 1px border + rounded corners + drop shadow" pattern (see frontend-design
 * skill anti-defaults). Hairline borders, restrained radii, no shadow on
 * the flush variant.
 *
 * Prefer `Panel` over `Card` in new work.
 */
export const Panel = React.forwardRef<HTMLElement, PanelProps>(
  (
    {
      variant = 'flush',
      unpadded = false,
      className,
      children,
      as = 'section',
      ...rest
    },
    ref
  ) => {
    const Component = as as React.ElementType
    return (
      <Component
        ref={ref}
        className={cn(
          'rounded-editorial border border-hairline',
          variant === 'flush'
            ? 'bg-canvas-raised/40'
            : 'bg-canvas-raised shadow-elevated',
          !unpadded && 'p-5 sm:p-6',
          className
        )}
        {...rest}
      >
        {children}
      </Component>
    )
  }
)

Panel.displayName = 'Panel'
