import { HealthCheck } from '@/components/HealthCheck'

function App() {
  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
          PaperTrade
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Stock market emulation platform
        </p>
      </header>

      <main className="space-y-6">
        <section>
          <h2 className="mb-4 text-2xl font-semibold text-gray-800 dark:text-gray-200">
            System Status
          </h2>
          <HealthCheck />
        </section>

        <section className="rounded-lg border border-gray-300 bg-gray-50 p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 text-2xl font-semibold text-gray-800 dark:text-gray-200">
            Welcome to PaperTrade
          </h2>
          <p className="text-gray-700 dark:text-gray-300">
            This is the frontend scaffolding for the PaperTrade application.
            Features will be added in subsequent phases.
          </p>
        </section>
      </main>
    </div>
  )
}

export default App
