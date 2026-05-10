import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Editorial input — flush hairline border on canvas-raised, ink text,
 * amber focus ring. Replaces the legacy "white pill with gray border" look.
 */
const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink transition-colors duration-quick ease-editorial file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink placeholder:text-ink-subtle focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Input.displayName = 'Input'

export { Input }
