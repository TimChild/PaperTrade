import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

/**
 * Editorial button (Wave 1).
 *
 * - `default` is amber-on-canvas — used for primary calls to action
 *   (place order, save). Restrained, no shadow.
 * - `secondary` is hairline-bordered, ink text — used for tertiary actions.
 * - `outline` is the same shape as secondary but with a transparent body
 *   and accent on hover.
 * - `ghost` is borderless — for inline navigation.
 * - `destructive` uses the muted loss tone.
 *
 * The default `rounded-button` token resolves to a small radius (0.25rem)
 * — no jelly buttons.
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-button text-sm font-medium tracking-tight transition-colors duration-quick ease-editorial focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-amber text-canvas hover:bg-amber-hover',
        secondary:
          'bg-canvas-raised text-ink hover:bg-canvas-raised/70 border border-hairline',
        outline:
          'border border-hairline-strong bg-transparent text-ink hover:border-amber hover:text-amber',
        ghost: 'text-ink-muted hover:text-ink hover:bg-canvas-raised/40',
        destructive: 'bg-loss text-canvas hover:bg-loss/90',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-button px-3',
        lg: 'h-11 rounded-button px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
