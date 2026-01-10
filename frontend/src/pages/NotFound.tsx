import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Home, ArrowLeft } from 'lucide-react'

/**
 * NotFound component - 404 page for invalid routes
 *
 * This page is displayed when a user navigates to a route that doesn't exist.
 * It follows the design system with proper spacing, typography, and theming.
 */
export function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* 404 Error Code */}
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-primary">404</h1>
        </div>

        {/* Error Message */}
        <h2 className="text-3xl font-bold text-foreground mb-4">
          Page Not Found
        </h2>

        <p className="text-lg text-muted-foreground mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            onClick={() => navigate(-1)}
            variant="outline"
            className="inline-flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Button>

          <Button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-2"
          >
            <Home className="h-4 w-4" />
            Return to Dashboard
          </Button>
        </div>

        {/* Helpful Links */}
        <div className="mt-12 pt-8 border-t border-border">
          <p className="text-sm text-muted-foreground mb-4">
            Looking for something specific?
          </p>
          <ul className="text-sm space-y-2">
            <li>
              <button
                onClick={() => navigate('/dashboard')}
                className="text-primary hover:underline"
              >
                View your portfolios
              </button>
            </li>
            <li>
              <a
                href="https://github.com/TimChild/PaperTrade"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Report an issue
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
