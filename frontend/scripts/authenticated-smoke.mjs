/* global console, fetch, process, URL, window */

import { createClerkClient } from '@clerk/backend'
import { chromium } from '@playwright/test'

const DEFAULT_MODE = 'auth'
const DEFAULT_TIMEOUT_MS = 30_000
const SMOKE_PREFIX = process.env.SMOKE_NAME_PREFIX || 'Smoke'
const SMOKE_PORTFOLIO_NAME = `${SMOKE_PREFIX} Portfolio`
const SMOKE_STRATEGY_NAME = `${SMOKE_PREFIX} Strategy`
const SMOKE_BACKTEST_NAME = `${SMOKE_PREFIX} Backtest`
const SMOKE_BACKTEST_PORTFOLIO_NAME = `[Backtest] ${SMOKE_BACKTEST_NAME}`
const SMOKE_TICKER = 'AAPL'

function parseArgs(argv) {
  const args = {
    mode: process.env.SMOKE_MODE || DEFAULT_MODE,
    appUrl: process.env.SMOKE_APP_URL,
    apiBaseUrl: process.env.SMOKE_API_BASE_URL,
    clerkSecretKey: process.env.SMOKE_CLERK_SECRET_KEY,
    userEmail: process.env.SMOKE_USER_EMAIL,
    headless: process.env.SMOKE_HEADLESS !== 'false',
  }

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]

    if (arg === '--mode') {
      args.mode = argv[index + 1]
      index += 1
      continue
    }

    if (arg === '--app-url') {
      args.appUrl = argv[index + 1]
      index += 1
      continue
    }

    if (arg === '--api-base-url') {
      args.apiBaseUrl = argv[index + 1]
      index += 1
      continue
    }

    if (arg === '--clerk-secret-key') {
      args.clerkSecretKey = argv[index + 1]
      index += 1
      continue
    }

    if (arg === '--user-email') {
      args.userEmail = argv[index + 1]
      index += 1
      continue
    }

    if (arg === '--headed') {
      args.headless = false
      continue
    }

    if (arg === '--headless') {
      args.headless = true
      continue
    }

    if (arg === '--help' || arg === '-h') {
      printHelp()
      process.exit(0)
    }

    throw new Error(`Unknown argument: ${arg}`)
  }

  return args
}

function printHelp() {
  console.log(`Authenticated smoke test

Required configuration:
  SMOKE_APP_URL
  SMOKE_API_BASE_URL
  SMOKE_CLERK_SECRET_KEY
  SMOKE_USER_EMAIL

Options:
  --mode auth|full
  --app-url URL
  --api-base-url URL
  --clerk-secret-key KEY
  --user-email EMAIL
  --headed
  --headless`)
}

function requireConfig(config) {
  const required = [
    ['appUrl', config.appUrl],
    ['apiBaseUrl', config.apiBaseUrl],
    ['clerkSecretKey', config.clerkSecretKey],
    ['userEmail', config.userEmail],
  ]

  const missing = required.filter(([, value]) => !value).map(([key]) => key)
  if (missing.length > 0) {
    throw new Error(`Missing required configuration: ${missing.join(', ')}`)
  }

  if (!['auth', 'full'].includes(config.mode)) {
    throw new Error(`Unsupported mode: ${config.mode}`)
  }
}

function logStep(message) {
  console.log(`\n[smoke] ${message}`)
}

function buildUrl(baseUrl, path) {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }

  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path
  return new URL(normalizedPath, normalizedBase).toString()
}

function summarizeText(text) {
  if (!text) {
    return ''
  }

  return text.replace(/\s+/g, ' ').trim().slice(0, 240)
}

function responseError(label, response, text) {
  return new Error(
    `${label} failed with ${response.status} ${response.statusText}: ${summarizeText(text)}`
  )
}

function toNumber(value) {
  return Number.parseFloat(String(value))
}

function toIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

function createCandidateWindow() {
  const end = new Date()
  end.setUTCHours(0, 0, 0, 0)
  end.setUTCDate(end.getUTCDate() - 3)

  const start = new Date(end)
  start.setUTCDate(start.getUTCDate() - 21)

  return {
    startDate: toIsoDate(start),
    endDate: toIsoDate(end),
  }
}

async function createSessionToken(config) {
  logStep(`Creating Clerk sign-in ticket for ${config.userEmail}`)

  const clerkClient = createClerkClient({
    secretKey: config.clerkSecretKey,
  })

  const users = await clerkClient.users.getUserList({
    emailAddress: [config.userEmail],
  })

  if (!users.data || users.data.length === 0) {
    throw new Error(`No Clerk user found for ${config.userEmail}`)
  }

  const user = users.data[0]
  const signInToken = await clerkClient.signInTokens.createSignInToken({
    userId: user.id,
    expiresInSeconds: 300,
  })

  const browser = await chromium.launch({ headless: config.headless })
  const page = await browser.newPage()

  try {
    logStep(`Loading app shell at ${config.appUrl}`)
    await page.goto(config.appUrl, { waitUntil: 'domcontentloaded' })
    await page.waitForFunction(() => Boolean(window.Clerk?.loaded), undefined, {
      timeout: DEFAULT_TIMEOUT_MS,
    })

    logStep('Activating browser session with Clerk ticket sign-in')
    const result = await page.evaluate(async (ticket) => {
      const signIn = await window.Clerk.client.signIn.create({
        strategy: 'ticket',
        ticket,
      })

      if (signIn.status !== 'complete') {
        return { error: `sign-in status was ${signIn.status}` }
      }

      await window.Clerk.setActive({ session: signIn.createdSessionId })

      if (!window.Clerk.session) {
        return { error: 'Clerk session was not created' }
      }

      const token = await window.Clerk.session.getToken()
      return token ? { token } : { error: 'Unable to retrieve session token' }
    }, signInToken.token)

    if (result.error) {
      throw new Error(result.error)
    }

    return result.token
  } finally {
    await page.close()
    await browser.close()
  }
}

function createApiClient(config, sessionToken) {
  async function request(method, path, body, expectedStatuses = [200]) {
    const url = buildUrl(config.apiBaseUrl, path)
    const response = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${sessionToken}`,
        'Content-Type': 'application/json',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    const text = await response.text()
    const contentType = response.headers.get('content-type') || ''
    const data = contentType.includes('application/json') && text ? JSON.parse(text) : text

    console.log(`[api] ${method} ${url} -> ${response.status}`)

    if (!expectedStatuses.includes(response.status)) {
      throw responseError(`${method} ${url}`, response, text)
    }

    return data
  }

  return {
    get: (path, expectedStatuses) => request('GET', path, undefined, expectedStatuses),
    post: (path, body, expectedStatuses = [200, 201]) =>
      request('POST', path, body, expectedStatuses),
    delete: (path, expectedStatuses = [204]) =>
      request('DELETE', path, undefined, expectedStatuses),
  }
}

async function runAuthSmoke(api) {
  logStep('Running authenticated read smoke')
  const portfolios = await api.get('/portfolios?limit=20&offset=0')
  console.log(`[smoke] Authenticated portfolio list returned ${portfolios.length} portfolio(s)`)
}

async function cleanupSmokeArtifacts(api) {
  logStep('Cleaning up older smoke artifacts with matching names')

  const backtests = await api.get('/backtests')
  for (const backtest of backtests.filter((item) => item.backtest_name === SMOKE_BACKTEST_NAME)) {
    await api.delete(`/backtests/${backtest.id}`)
  }

  const strategies = await api.get('/strategies')
  for (const strategy of strategies.filter((item) => item.name === SMOKE_STRATEGY_NAME)) {
    await api.delete(`/strategies/${strategy.id}`)
  }

  const portfolios = await api.get('/portfolios?include_backtest=true&limit=100&offset=0')
  for (const portfolio of portfolios.filter(
    (item) => item.name === SMOKE_PORTFOLIO_NAME || item.name === SMOKE_BACKTEST_PORTFOLIO_NAME
  )) {
    await api.delete(`/portfolios/${portfolio.id}`)
  }
}

async function loadPriceHistory(api, startDate, endDate) {
  return api.get(
    `/prices/${SMOKE_TICKER}/history?start=${encodeURIComponent(
      `${startDate}T00:00:00Z`
    )}&end=${encodeURIComponent(`${endDate}T23:59:59Z`)}&interval=1day`,
    [200]
  )
}

async function resolveBacktestWindow(api) {
  const candidateWindow = createCandidateWindow()

  logStep(
    `Resolving a recent backtest window for ${SMOKE_TICKER} between ${candidateWindow.startDate} and ${candidateWindow.endDate}`
  )

  let history = await loadPriceHistory(
    api,
    candidateWindow.startDate,
    candidateWindow.endDate
  )

  if (history.count < 3) {
    logStep(`Fetching recent historical data for ${SMOKE_TICKER}`)
    const fetchResult = await api.post('/prices/fetch-historical', {
      ticker: SMOKE_TICKER,
      start: `${candidateWindow.startDate}T00:00:00Z`,
      end: `${candidateWindow.endDate}T23:59:59Z`,
    })

    console.log(`[smoke] Fetched ${fetchResult.fetched} historical price point(s)`)
    history = await loadPriceHistory(
      api,
      candidateWindow.startDate,
      candidateWindow.endDate
    )
  }

  if (history.count < 3) {
    throw new Error(
      `Unable to find enough recent history for ${SMOKE_TICKER} in ${candidateWindow.startDate}..${candidateWindow.endDate}`
    )
  }

  const startDate = history.prices[0].timestamp.slice(0, 10)
  const endDate = history.prices[history.prices.length - 1].timestamp.slice(0, 10)

  console.log(`[smoke] Using backtest window ${startDate}..${endDate}`)
  return { startDate, endDate }
}

async function ensureHistoricalData(api, window) {
  logStep(`Checking historical data availability for ${SMOKE_TICKER}`)
  const checkPath = `/prices/${SMOKE_TICKER}/check?date=${encodeURIComponent(
    `${window.startDate}T12:00:00Z`
  )}`

  const check = await api.get(checkPath, [200])

  if (check.available) {
    console.log(`[smoke] Historical data already available for ${SMOKE_TICKER}`)
    return
  }

  logStep(`Fetching historical data for ${SMOKE_TICKER}`)
  const fetchResult = await api.post('/prices/fetch-historical', {
    ticker: SMOKE_TICKER,
    start: `${window.startDate}T00:00:00Z`,
    end: `${window.endDate}T23:59:59Z`,
  })

  console.log(`[smoke] Fetched ${fetchResult.fetched} historical price point(s)`)

  const recheck = await api.get(checkPath, [200])
  if (!recheck.available) {
    throw new Error(
      `Historical data for ${SMOKE_TICKER} is still unavailable after fetch attempt`
    )
  }
}

async function runFullSmoke(api) {
  await cleanupSmokeArtifacts(api)
  const backtestWindow = await resolveBacktestWindow(api)
  await ensureHistoricalData(api, backtestWindow)

  logStep('Creating smoke portfolio')
  const createdPortfolio = await api.post('/portfolios', {
    name: SMOKE_PORTFOLIO_NAME,
    initial_deposit: 1000,
    currency: 'USD',
  })

  const portfolios = await api.get('/portfolios?limit=100&offset=0')
  const smokePortfolio = portfolios.find((portfolio) => portfolio.id === createdPortfolio.portfolio_id)
  if (!smokePortfolio) {
    throw new Error('Smoke portfolio was not returned by list endpoint')
  }

  const smokeBalance = await api.get(`/portfolios/${createdPortfolio.portfolio_id}/balance`)
  if (toNumber(smokeBalance.cash_balance) < 1000) {
    throw new Error(`Unexpected smoke portfolio cash balance: ${smokeBalance.cash_balance}`)
  }

  logStep('Creating buy-and-hold smoke strategy')
  const strategy = await api.post('/strategies', {
    name: SMOKE_STRATEGY_NAME,
    strategy_type: 'BUY_AND_HOLD',
    tickers: [SMOKE_TICKER],
    parameters: {
      allocation: {
        [SMOKE_TICKER]: 1,
      },
    },
  })

  logStep('Running smoke backtest')
  const backtest = await api.post('/backtests', {
    strategy_id: strategy.id,
    backtest_name: SMOKE_BACKTEST_NAME,
    start_date: backtestWindow.startDate,
    end_date: backtestWindow.endDate,
    initial_cash: 10000,
  })

  const backtestDetails = await api.get(`/backtests/${backtest.id}`)
  if (backtestDetails.status !== 'COMPLETED') {
    const detail = backtestDetails.error_message
      ? `: ${backtestDetails.error_message}`
      : ''
    throw new Error(
      `Expected backtest to complete, got ${backtestDetails.status}${detail}`
    )
  }

  const backtestTransactions = await api.get(
    `/portfolios/${backtest.portfolio_id}/transactions?limit=20&offset=0`
  )

  const depositCount = backtestTransactions.transactions.filter(
    (transaction) => transaction.transaction_type === 'DEPOSIT'
  ).length
  const buyCount = backtestTransactions.transactions.filter(
    (transaction) => transaction.transaction_type === 'BUY'
  ).length
  const sellCount = backtestTransactions.transactions.filter(
    (transaction) => transaction.transaction_type === 'SELL'
  ).length

  if (depositCount !== 1) {
    throw new Error(`Expected exactly 1 backtest deposit transaction, got ${depositCount}`)
  }

  if (buyCount !== 1) {
    throw new Error(`Expected exactly 1 BUY transaction for buy-and-hold backtest, got ${buyCount}`)
  }

  if (sellCount !== 0) {
    throw new Error(`Expected 0 SELL transactions for buy-and-hold backtest, got ${sellCount}`)
  }

  if (backtestDetails.total_trades !== 1) {
    throw new Error(`Expected total_trades=1, got ${backtestDetails.total_trades}`)
  }

  console.log('\n[smoke] Full smoke summary')
  console.log(`- Portfolio: ${createdPortfolio.portfolio_id}`)
  console.log(`- Strategy: ${strategy.id}`)
  console.log(`- Backtest: ${backtest.id}`)
  console.log(`- Backtest portfolio: ${backtest.portfolio_id}`)
  console.log(`- Backtest return: ${backtestDetails.total_return_pct ?? 'n/a'}%`)
}

async function main() {
  const config = parseArgs(process.argv.slice(2))
  requireConfig(config)

  console.log('[smoke] Configuration')
  console.log(`- Mode: ${config.mode}`)
  console.log(`- App URL: ${config.appUrl}`)
  console.log(`- API Base URL: ${config.apiBaseUrl}`)
  console.log(`- User Email: ${config.userEmail}`)
  console.log(`- Browser: ${config.headless ? 'headless' : 'headed'}`)

  const sessionToken = await createSessionToken(config)
  const api = createApiClient(config, sessionToken)

  await runAuthSmoke(api)

  if (config.mode === 'full') {
    await runFullSmoke(api)
  }

  logStep('Smoke test completed successfully')
}

main().catch((error) => {
  console.error(`\n[smoke] Failed: ${error.message}`)
  process.exitCode = 1
})
