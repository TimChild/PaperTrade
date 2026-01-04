import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
} from '@clerk/clerk-react'
import { Dashboard } from '@/pages/Dashboard'
import { PortfolioDetail } from '@/pages/PortfolioDetail'
import { useAuthenticatedApi } from '@/hooks/useAuthenticatedApi'

function App() {
  // Set up authenticated API client
  useAuthenticatedApi()

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="container mx-auto flex items-center justify-between px-4 py-4">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">PaperTrade</h1>
            <SignedOut>
              <div className="flex gap-2">
                <SignInButton mode="modal">
                  <button className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                    Sign In
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button className="rounded-lg border border-gray-300 bg-white px-4 py-2 font-semibold text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                    Sign Up
                  </button>
                </SignUpButton>
              </div>
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
          </div>
        </header>

        <main>
          <SignedOut>
            <div className="flex min-h-[80vh] items-center justify-center">
              <div className="text-center">
                <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
                  Welcome to PaperTrade
                </h2>
                <p className="mb-6 text-gray-600 dark:text-gray-400">
                  Sign in to start trading
                </p>
                <SignInButton mode="modal">
                  <button className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                    Get Started
                  </button>
                </SignInButton>
              </div>
            </div>
          </SignedOut>
          <SignedIn>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/portfolio/:id" element={<PortfolioDetail />} />
            </Routes>
          </SignedIn>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
