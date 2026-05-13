import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
} from 'react-router-dom'
import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react'
import { Toaster } from 'react-hot-toast'
import { Dashboard } from '@/pages/Dashboard'
import { PortfolioDetail } from '@/pages/PortfolioDetail'
import { PortfolioAnalytics } from '@/pages/PortfolioAnalytics'
import { Strategies } from '@/pages/Strategies'
import { StrategyDetail } from '@/pages/StrategyDetail'
import { Activations } from '@/pages/Activations'
import { ActivationDetail } from '@/pages/ActivationDetail'
import { TriggerFireLog } from '@/pages/TriggerFireLog'
import { ExplorationTasks } from '@/pages/ExplorationTasks'
import { ExplorationTaskDetail } from '@/pages/ExplorationTaskDetail'
import { Activity } from '@/pages/Activity'
import { Backtests } from '@/pages/Backtests'
import { BacktestResult } from '@/pages/BacktestResult'
import { CompareBacktests } from '@/pages/CompareBacktests'
import { SettingsApiKeys } from '@/pages/SettingsApiKeys'
import { SettingsLayout } from '@/components/SettingsLayout'
import { AdminLayout } from '@/components/AdminLayout'
import { AdminDataCoverage } from '@/pages/AdminDataCoverage'
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
            // Editorial dark: warm canvas backplate + ink, with muted gain/loss
            // icon tones — never neon green/red.
            style: {
              background: '#13181f',
              color: '#ece7df',
              border: '1px solid hsl(215 12% 22%)',
              borderRadius: '0.25rem',
              fontFamily:
                "'IBM Plex Sans Variable', 'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '0.875rem',
              boxShadow:
                '0 14px 40px -22px rgba(0, 0, 0, 0.6), 0 4px 8px -4px rgba(0, 0, 0, 0.4)',
            },
            success: {
              duration: 5000,
              iconTheme: {
                primary: '#6ba283', // muted gain (matches --gain)
                secondary: '#13181f',
              },
            },
            error: {
              duration: 7000,
              iconTheme: {
                primary: '#c46a64', // muted loss (matches --loss)
                secondary: '#13181f',
              },
            },
          }}
        />
        <Routes>
          <Route path="*" element={<AuthenticatedApp />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

function AuthenticatedApp() {
  return (
    <div className="min-h-screen bg-canvas">
      <SignedOut>
        {/* Show sign-in page when user is not authenticated */}
        <div className="flex min-h-screen items-center justify-center bg-canvas">
          <div className="w-full max-w-md px-6">
            <div className="mb-8 text-center">
              <p className="font-eyebrow text-ink-muted">Practice trading</p>
              <h1 className="mt-2 font-display text-display-lg tracking-tight text-ink">
                Zebu
              </h1>
              <p className="mt-3 text-body-md text-ink-muted">
                Backtest. Refine. Trade — without risk.
              </p>
            </div>
            <SignIn
              routing="hash"
              signUpUrl="#/sign-up"
              appearance={{
                elements: {
                  rootBox: 'mx-auto',
                  card: 'shadow-elevated',
                },
              }}
            />
          </div>
        </div>
      </SignedOut>

      <SignedIn>
        {/* Show app when user is authenticated. Editorial chrome: hairline
            border under the header, generous gutters, no card-with-shadow. */}
        <div className="flex min-h-screen flex-col bg-canvas">
          <header className="border-b border-hairline bg-canvas">
            <div className="mx-auto flex max-w-[1240px] items-center justify-between px-5 sm:px-8 lg:px-12 py-4 sm:py-5">
              <h1 className="font-display text-2xl tracking-tight text-ink">
                Zebu
              </h1>
              <UserButton afterSignOutUrl="/" />
            </div>
          </header>

          {/* Navigation — editorial tabs. Underline on active, ink-muted on rest. */}
          <nav className="border-b border-hairline bg-canvas">
            <div className="mx-auto max-w-[1240px] px-5 sm:px-8 lg:px-12">
              <div className="flex gap-0">
                {[
                  { to: '/dashboard', label: 'Portfolios', end: true },
                  { to: '/strategies', label: 'Strategies', end: false },
                  { to: '/activations', label: 'Activations', end: false },
                  {
                    to: '/exploration-tasks',
                    label: 'Exploration tasks',
                    end: false,
                  },
                  { to: '/backtests', label: 'Backtests', end: false },
                  { to: '/admin', label: 'Admin', end: false },
                  { to: '/settings', label: 'Settings', end: false },
                ].map(({ to, label, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    className={({ isActive }) =>
                      `relative px-4 py-3.5 text-body-sm font-medium tracking-tight transition-colors duration-quick ease-editorial ${
                        isActive
                          ? 'text-amber after:absolute after:left-4 after:right-4 after:-bottom-px after:h-px after:bg-amber'
                          : 'text-ink-muted hover:text-ink'
                      }`
                    }
                    style={{ minHeight: 'auto' }}
                  >
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          </nav>

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
              <Route path="/strategies" element={<Strategies />} />
              <Route path="/strategies/:id" element={<StrategyDetail />} />
              <Route path="/activations" element={<Activations />} />
              <Route path="/activations/:id" element={<ActivationDetail />} />
              <Route path="/triggers/:id/fires" element={<TriggerFireLog />} />
              <Route path="/exploration-tasks" element={<ExplorationTasks />} />
              <Route
                path="/exploration-tasks/:id"
                element={<ExplorationTaskDetail />}
              />
              <Route path="/activity" element={<Activity />} />
              <Route path="/backtests" element={<Backtests />} />
              <Route path="/backtests/:id" element={<BacktestResult />} />
              <Route path="/compare" element={<CompareBacktests />} />
              <Route path="/settings" element={<SettingsLayout />}>
                <Route
                  index
                  element={<Navigate to="/settings/api-keys" replace />}
                />
                <Route path="api-keys" element={<SettingsApiKeys />} />
              </Route>
              {/* Phase J / Task #212 Layer 4 — admin data-coverage UI. */}
              <Route path="/admin" element={<AdminLayout />}>
                <Route
                  index
                  element={<Navigate to="/admin/data-coverage" replace />}
                />
                <Route path="data-coverage" element={<AdminDataCoverage />} />
              </Route>
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
