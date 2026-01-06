import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react'
import { Dashboard } from '@/pages/Dashboard'
import { PortfolioDetail } from '@/pages/PortfolioDetail'
import { PortfolioAnalytics } from '@/pages/PortfolioAnalytics'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <SignedOut>
          {/* Show sign-in page when user is not authenticated */}
          <div className="flex min-h-screen items-center justify-center">
            <div className="w-full max-w-md">
              <div className="mb-8 text-center">
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
                  PaperTrade
                </h1>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  Practice trading without risking real money
                </p>
              </div>
              <SignIn
                routing="hash"
                signUpUrl="#/sign-up"
                appearance={{
                  elements: {
                    rootBox: 'mx-auto',
                    card: 'shadow-xl',
                  },
                }}
              />
            </div>
          </div>
        </SignedOut>

        <SignedIn>
          {/* Show app when user is authenticated */}
          <div className="flex min-h-screen flex-col">
            {/* Header with user button */}
            <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-800">
              <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  PaperTrade
                </h1>
                <UserButton afterSignOutUrl="/" />
              </div>
            </header>

            {/* Main content */}
            <main className="flex-1">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/portfolio/:id" element={<PortfolioDetail />} />
                <Route path="/portfolio/:id/analytics" element={<PortfolioAnalytics />} />
              </Routes>
            </main>
          </div>
        </SignedIn>
      </div>
    </BrowserRouter>
  )
}

export default App
