/**
 * Editorial loading spinner — hairline ring with an amber arc segment.
 * Quiet, no neon accents.
 */
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({
  size = 'md',
  className = '',
}: LoadingSpinnerProps): React.JSX.Element {
  const sizeClasses = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-[3px]',
    lg: 'h-12 w-12 border-[3px]',
  }

  return (
    <div
      className={`flex items-center justify-center ${className}`}
      data-testid="loading-spinner"
    >
      <div
        className={`${sizeClasses[size]} animate-spin rounded-full border-hairline border-t-amber`}
        role="status"
        aria-label="Loading"
      >
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  )
}
