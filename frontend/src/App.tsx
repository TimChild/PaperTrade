import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react'
import { Toaster } from 'react-hot-toast'
import { Dashboard } from '@/pages/Dashboard'
import { PortfolioDetail } from '@/pages/PortfolioDetail'
import { PortfolioAnalytics } from '@/pages/PortfolioAnalytics'
import { Debug } from '@/pages/Debug'
import { NotFound } from '@/pages/NotFound'
import { DashboardVariantA } from '@/pages/__prototypes__/DashboardVariantA'
import { DashboardVariantB } from '@/pages/__prototypes__/DashboardVariantB'
import { ThemeProvider } from '@/contexts/ThemeContext'

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 5000,
            success: {
              duration: 5000,
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              duration: 7000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
        <Routes>
          {/* Debug route - accessible without authentication */}
          <Route path="/debug" element={<Debug />} />

          {/* All other routes */}
          <Route path="*" element={<AuthenticatedApp />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

function AuthenticatedApp() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <SignedOut>
        {/* Show sign-in page when user is not authenticated */}
        <div className="flex min-h-screen items-center justify-center">
          <div className="w-full max-w-md">
            <div className="mb-8 text-center">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
                Zebu
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
            <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                Zebu
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
              <Route
                path="/portfolio/:id/analytics"
                element={<PortfolioAnalytics />}
              />
              {/* Prototype routes (dev only) */}
              {import.meta.env.DEV && (
                <>
                  <Route
                    path="/prototypes/dashboard-a"
                    element={<DashboardVariantA />}
                  />
                  <Route
                    path="/prototypes/dashboard-b"
                    element={<DashboardVariantB />}
                  />
                </>
              )}
              {/* 404 Not Found route - must be last */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </SignedIn>
    </div>
  )
}

export default App
