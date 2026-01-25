# Playwright MCP Usage Guide

This guide covers using the Playwright MCP (Model Context Protocol) server for browser automation and UI debugging in the Zebu project.

## Overview

The Playwright MCP allows AI agents to control a browser programmatically for:
- Manual testing and UI verification
- Debugging frontend issues
- Capturing screenshots for documentation
- Inspecting React component state and network requests

## Prerequisites

1. **Docker services running**: `task docker:up:all`
2. **Frontend accessible**: http://localhost:5173
3. **Backend accessible**: http://localhost:8000

## Authentication

### Test User Credentials
- **Email**: `orchestrator+clerk_test@papertrade.dev`
- **Password**: `test-clerk-password`
- **2FA Code** (if prompted): `424242` (test account uses fixed code)

### Sign-In Flow

Clerk uses a two-step sign-in process:

```
1. Navigate to http://localhost:5173
2. Enter email in "Email address" field
3. Click "Continue"
4. On password page, enter password
5. Click "Continue"
6. If 2FA prompted, enter "424242"
7. Wait for redirect to /dashboard
```

**Example using Playwright MCP:**
```
1. mcp_microsoft_pla_browser_navigate: url="http://localhost:5173"
2. mcp_microsoft_pla_browser_type: ref=<email_field>, text="orchestrator+clerk_test@papertrade.dev"
3. mcp_microsoft_pla_browser_click: ref=<continue_button>
4. Wait for password page, then:
5. mcp_microsoft_pla_browser_type: ref=<password_field>, text="test-clerk-password"
6. mcp_microsoft_pla_browser_click: ref=<continue_button>
7. If 2FA page appears:
   mcp_microsoft_pla_browser_type: ref=<totp_field>, text="424242"
   mcp_microsoft_pla_browser_click: ref=<continue_button>
```

## Common Operations

### Taking Screenshots
```
mcp_microsoft_pla_browser_take_screenshot:
  filename: "temp/my_screenshot.png"
  type: "png"
```

For full page screenshots:
```
mcp_microsoft_pla_browser_take_screenshot:
  filename: "temp/full_page.png"
  type: "png"
  fullPage: true
```

### Getting Page Snapshot (Accessibility Tree)
More useful than screenshots for understanding page structure:
```
mcp_microsoft_pla_browser_snapshot
```

Returns a YAML representation of the page with element references (e.g., `ref=e123`) that can be used for clicking, typing, etc.

### Checking Network Requests
```
mcp_microsoft_pla_browser_network_requests:
  includeStatic: false
```

Returns all API calls made by the page, useful for debugging backend integration.

### Running Custom JavaScript
For advanced debugging (e.g., inspecting React state):
```
mcp_microsoft_pla_browser_run_code:
  code: |
    async (page) => {
      const result = await page.evaluate(() => {
        // Access DOM, React DevTools, etc.
        return document.title;
      });
      return result;
    }
```

### Getting Console Messages
```
mcp_microsoft_pla_browser_console_messages:
  level: "error"  # or "warning", "info", "debug"
```

## Debugging React Components

### Inspecting Component Props via React Fiber
```javascript
async (page) => {
  const result = await page.evaluate(() => {
    function findReactFiber(dom) {
      const key = Object.keys(dom).find(key =>
        key.startsWith('__reactFiber$') ||
        key.startsWith('__reactInternalInstance$')
      );
      return key ? dom[key] : null;
    }

    const element = document.querySelector('.my-component');
    const fiber = findReactFiber(element);

    // Walk up fiber tree to find component with data
    let current = fiber;
    for (let i = 0; i < 20 && current; i++) {
      if (current.memoizedProps?.data) {
        return current.memoizedProps.data;
      }
      current = current.return;
    }
    return null;
  });
  return JSON.stringify(result, null, 2);
}
```

### Intercepting API Responses
```javascript
async (page) => {
  let capturedResponse = null;

  page.on('response', async (response) => {
    if (response.url().includes('/api/v1/portfolios')) {
      capturedResponse = await response.json();
    }
  });

  // Trigger action that makes API call
  await page.click('[data-testid="refresh-button"]');
  await page.waitForTimeout(2000);

  return JSON.stringify(capturedResponse, null, 2);
}
```

## Common Patterns

### Wait for Navigation
```javascript
await page.waitForURL('**/dashboard**', { timeout: 15000 });
```

### Wait for Element
```javascript
await page.waitForSelector('[data-testid="portfolio-card"]');
```

### Click with Exact Match
When multiple buttons have similar names:
```javascript
await page.getByRole('button', { name: 'Continue', exact: true }).click();
```

## Troubleshooting

### "Password compromised" Error
Clerk's breach detection may flag common passwords. Use the test password: `test-clerk-password`

### 2FA Prompt
Test accounts use TOTP code: `424242`

### Browser Not Installed
Run: `mcp_microsoft_pla_browser_install`

### Element Not Found
1. Take a snapshot first: `mcp_microsoft_pla_browser_snapshot`
2. Find the correct `ref` value
3. Use that ref in subsequent operations

### Timeout Errors
- Increase timeout in `waitForURL` or similar calls
- Check if Docker services are running: `task docker:ps`
- Check backend logs: `task docker:logs:backend`

## Best Practices

1. **Always get a snapshot first** before interacting with elements
2. **Use `ref` values** from snapshots rather than guessing selectors
3. **Save screenshots to `temp/`** directory (gitignored)
4. **Check network requests** when debugging API integration issues
5. **Use `run_code` sparingly** - prefer built-in MCP actions when possible
6. **Close browser when done**: `mcp_microsoft_pla_browser_close`

## Limitations

- Cannot access browser DevTools directly (use `run_code` instead)
- Screenshot quality is fixed (CSS scale)
- Some Clerk UI elements have dynamic refs that change between renders
- Session tokens expire - may need to re-authenticate for long sessions
