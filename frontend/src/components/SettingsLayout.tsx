/**
 * Settings shell — left-rail nav + content. Single section today (API keys);
 * profile / notifications etc. will slot in later without restructuring.
 */
import { NavLink, Outlet } from 'react-router-dom'

interface SettingsNavItem {
  to: string
  label: string
  testId: string
}

const NAV_ITEMS: SettingsNavItem[] = [
  {
    to: '/settings/api-keys',
    label: 'API Keys',
    testId: 'settings-nav-api-keys',
  },
]

export function SettingsLayout(): React.JSX.Element {
  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="settings-layout"
    >
      <div className="grid grid-cols-1 gap-8 md:grid-cols-[200px_1fr]">
        <nav
          className="flex flex-row gap-2 md:flex-col md:gap-1"
          aria-label="Settings sections"
        >
          {NAV_ITEMS.map(({ to, label, testId }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testId}
              className={({ isActive }) =>
                `rounded-button px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary text-white'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <section>
          <Outlet />
        </section>
      </div>
    </div>
  )
}
