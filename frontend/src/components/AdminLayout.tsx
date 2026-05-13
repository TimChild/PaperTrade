/**
 * Admin shell — left-rail nav + content. Mirrors `SettingsLayout` so the
 * admin section visually rhymes with the rest of the app. Today the only
 * surface is the data-coverage page (Phase J / Task #212 Layer 4);
 * future admin entries (triggers kill-switch, job-health UI) plug into
 * this same nav.
 *
 * Auth note: the page surfaces are gated on the backend (`AdminUserDep`).
 * The sidebar always renders for SignedIn users — non-admin users will
 * just see 403 errors when they hit the underlying endpoints. The full
 * "hide-the-nav-for-non-admins" treatment lands when we have a Clerk-
 * side admin claim wired (out of scope for L4).
 */
import { NavLink, Outlet } from 'react-router-dom'

interface AdminNavItem {
  to: string
  label: string
  testId: string
}

const NAV_ITEMS: AdminNavItem[] = [
  {
    to: '/admin/data-coverage',
    label: 'Data coverage',
    testId: 'admin-nav-data-coverage',
  },
]

export function AdminLayout(): React.JSX.Element {
  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="admin-layout"
    >
      <div className="grid grid-cols-1 gap-8 md:grid-cols-[200px_1fr]">
        <nav
          className="flex flex-row gap-2 md:flex-col md:gap-1"
          aria-label="Admin sections"
        >
          {NAV_ITEMS.map(({ to, label, testId }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testId}
              className={({ isActive }) =>
                `rounded-button px-3 py-2 text-body-sm font-medium tracking-tight transition-colors duration-quick ease-editorial ${
                  isActive
                    ? 'bg-amber text-canvas'
                    : 'text-ink-muted hover:bg-canvas-raised/40 hover:text-ink'
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
