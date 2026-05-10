import { cn } from '@/lib/utils'

interface CaptionProps extends React.HTMLAttributes<HTMLSpanElement> {
  className?: string
  children: React.ReactNode
}

/**
 * Low-emphasis fine-print caption. Used for "Last updated: 14:23:08",
 * data-source attributions, etc. Small caps at default size, neutral ink.
 */
export function Caption({
  className,
  children,
  ...rest
}: CaptionProps): React.JSX.Element {
  return (
    <span
      className={cn('font-caption', className)}
      data-testid="caption"
      {...rest}
    >
      {children}
    </span>
  )
}
