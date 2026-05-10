import { cn } from '@/lib/utils'

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-editorial bg-canvas-raised/80 dark:bg-canvas-raised/80',
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
