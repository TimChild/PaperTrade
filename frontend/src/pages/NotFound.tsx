import { useNavigate } from 'react-router-dom'
import { Home, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Eyebrow } from '@/components/ui/Eyebrow'

/**
 * Editorial 404 — eyebrow ("Page not found"), 404 in display serif as a
 * supersized number, supporting copy, two CTAs.
 *
 * Sits centered against the bare canvas — no card chrome.
 */
export function NotFound(): React.JSX.Element {
  const navigate = useNavigate()

  return (
    <div className="min-h-[80vh] bg-canvas flex items-center justify-center px-6">
      <div className="text-center max-w-md w-full">
        <Eyebrow>Page not found</Eyebrow>
        <p
          className="mt-3 font-display text-[6rem] sm:text-[8rem] leading-none tracking-tight text-amber tabular-nums"
          aria-hidden="true"
        >
          404
        </p>
        <h1 className="mt-4 font-display text-display-md text-ink">
          Nothing here
        </h1>
        <p className="mt-3 text-body-sm text-ink-muted">
          The page you&rsquo;re looking for doesn&rsquo;t exist or has been
          moved.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            onClick={() => navigate(-1)}
            variant="secondary"
            className="inline-flex items-center gap-2"
            data-testid="not-found-back-button"
          >
            <ArrowLeft className="h-4 w-4" />
            Go back
          </Button>

          <Button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-2"
            data-testid="not-found-home-button"
          >
            <Home className="h-4 w-4" />
            Return to dashboard
          </Button>
        </div>

        <div className="mt-12 pt-8 border-t border-hairline">
          <Eyebrow>Quick links</Eyebrow>
          <ul className="mt-3 text-body-sm space-y-2">
            <li>
              <button
                onClick={() => navigate('/dashboard')}
                className="text-amber hover:text-amber-hover transition-colors"
                style={{ minHeight: 'auto' }}
              >
                View your portfolios
              </button>
            </li>
            <li>
              <a
                href="https://github.com/TimChild/PaperTrade"
                target="_blank"
                rel="noopener noreferrer"
                className="text-amber hover:text-amber-hover transition-colors"
                style={{ minHeight: 'auto' }}
              >
                Report an issue on GitHub
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
