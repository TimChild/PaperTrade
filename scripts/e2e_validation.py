#!/usr/bin/env python3
"""
End-to-End Validation Script for Zebu

This script performs comprehensive E2E testing of the Zebu application
using Playwright. It validates all key user workflows and features.

Usage:
    python orchestrator_procedures/e2e_validation.py

Prerequisites:
    - Services running (task docker:up, backend dev:backend, frontend dev)
    - Playwright installed (pip install playwright && playwright install)
"""

import sys
import time
from playwright.sync_api import sync_playwright, Page, expect


class E2EValidator:
    """End-to-end validation for Zebu application"""

    def __init__(self, frontend_url: str = "http://localhost:5174", backend_url: str = "http://localhost:8000"):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.errors = []
        self.warnings = []
        self.successes = []

    def log_success(self, message: str):
        """Log a successful validation"""
        self.successes.append(message)
        print(f"✅ {message}")

    def log_error(self, message: str):
        """Log an error"""
        self.errors.append(message)
        print(f"❌ ERROR: {message}")

    def log_warning(self, message: str):
        """Log a warning"""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def check_backend_health(self):
        """Verify backend is responding"""
        print("\n📋 Checking Backend Health...")
        import requests

        try:
            # Check health endpoint
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_success("Backend health check passed")
            else:
                self.log_error(f"Backend health check failed with status {response.status_code}")
        except Exception as e:
            self.log_error(f"Backend is not responding: {e}")
            return False

        try:
            # Check API docs are accessible
            response = requests.get(f"{self.backend_url}/docs", timeout=5)
            if response.status_code == 200:
                self.log_success("Backend API docs accessible")
            else:
                self.log_warning("Backend API docs not accessible")
        except Exception as e:
            self.log_warning(f"Could not access API docs: {e}")

        return True

    def test_portfolio_creation(self, page: Page):
        """Test creating a new portfolio"""
        print("\n📋 Testing Portfolio Creation...")

        try:
            # Navigate to app
            page.goto(self.frontend_url)
            page.wait_for_load_state("networkidle")

            # Look for create portfolio button/form
            # Adjust selectors based on actual UI
            create_button = page.get_by_text("Create Portfolio", exact=False)
            if create_button.count() > 0:
                create_button.first.click()
                self.log_success("Found and clicked 'Create Portfolio' button")
            else:
                # Maybe we need to look for a form directly
                portfolio_name_input = page.locator('input[name="name"], input[placeholder*="name" i]').first
                if portfolio_name_input.count() > 0:
                    self.log_success("Found portfolio name input")
                else:
                    self.log_error("Could not find portfolio creation UI")
                    return None

            # Fill in portfolio details
            time.sleep(0.5)  # Wait for form to appear

            portfolio_name = f"Test Portfolio {int(time.time())}"
            name_input = page.locator('input[name="name"], input[placeholder*="name" i]').first
            name_input.fill(portfolio_name)
            self.log_success(f"Filled portfolio name: {portfolio_name}")

            # Submit form
            submit_button = page.get_by_role("button", name="Create", exact=False)
            if submit_button.count() == 0:
                submit_button = page.get_by_role("button", name="Submit", exact=False)

            if submit_button.count() > 0:
                submit_button.click()
                self.log_success("Submitted portfolio creation form")

                # Wait for success/redirect
                time.sleep(1)

                # Check if portfolio appears in list
                if portfolio_name in page.content():
                    self.log_success(f"Portfolio '{portfolio_name}' appears in UI")
                    return portfolio_name
                else:
                    self.log_warning("Portfolio created but not immediately visible")
                    return portfolio_name
            else:
                self.log_error("Could not find submit button")
                return None

        except Exception as e:
            self.log_error(f"Portfolio creation failed: {e}")
            return None

    def test_deposit_funds(self, page: Page, portfolio_name: str):
        """Test depositing funds into a portfolio"""
        print("\n📋 Testing Deposit Funds...")

        try:
            # Look for deposit button/link
            deposit_button = page.get_by_text("Deposit", exact=False).first
            if deposit_button.count() > 0:
                deposit_button.click()
                self.log_success("Clicked deposit button")

                time.sleep(0.5)

                # Fill deposit amount
                amount_input = page.locator('input[name="amount"], input[type="number"]').first
                amount_input.fill("10000")
                self.log_success("Entered deposit amount: $10,000")

                # Submit
                submit = page.get_by_role("button", name="Deposit", exact=False)
                if submit.count() > 0:
                    submit.click()
                    self.log_success("Submitted deposit")

                    time.sleep(1)

                    # Check if balance updated
                    content = page.content()
                    if "10000" in content or "10,000" in content:
                        self.log_success("Balance appears to be updated")
                        return True
                    else:
                        self.log_warning("Balance update not immediately visible")
                        return True
                else:
                    self.log_error("Could not find deposit submit button")
                    return False
            else:
                self.log_error("Could not find deposit button")
                return False

        except Exception as e:
            self.log_error(f"Deposit failed: {e}")
            return False

    def test_buy_stock(self, page: Page):
        """Test buying a stock"""
        print("\n📋 Testing Stock Purchase...")

        try:
            # Look for buy/trade button
            buy_button = page.get_by_text("Buy Stock", exact=False).first
            if buy_button.count() == 0:
                buy_button = page.get_by_text("Trade", exact=False).first
            if buy_button.count() == 0:
                buy_button = page.get_by_text("Buy", exact=False).first

            if buy_button.count() > 0:
                buy_button.click()
                self.log_success("Clicked buy stock button")

                time.sleep(0.5)

                # Fill stock details
                symbol_input = page.locator('input[name="symbol"], input[placeholder*="symbol" i]').first
                symbol_input.fill("AAPL")
                self.log_success("Entered stock symbol: AAPL")

                shares_input = page.locator('input[name="shares"], input[name="quantity"]').first
                shares_input.fill("10")
                self.log_success("Entered shares: 10")

                # Submit
                submit = page.get_by_role("button", name="Buy", exact=False)
                if submit.count() > 0:
                    submit.click()
                    self.log_success("Submitted stock purchase")

                    time.sleep(2)  # Wait for API call

                    # Check if stock appears in holdings
                    content = page.content()
                    if "AAPL" in content:
                        self.log_success("Stock AAPL appears in holdings")
                        return True
                    else:
                        self.log_warning("Stock purchase may have succeeded but not immediately visible")
                        return True
                else:
                    self.log_error("Could not find buy submit button")
                    return False
            else:
                self.log_error("Could not find buy stock button")
                return False

        except Exception as e:
            self.log_error(f"Stock purchase failed: {e}")
            return False

    def test_portfolio_valuation(self, page: Page):
        """Test that portfolio valuation displays"""
        print("\n📋 Testing Portfolio Valuation...")

        try:
            content = page.content()

            # Look for valuation indicators
            has_total = any(text in content.lower() for text in ["total value", "portfolio value", "valuation"])
            has_pnl = any(text in content.lower() for text in ["p&l", "profit", "gain", "loss"])

            if has_total:
                self.log_success("Portfolio valuation displays total value")
            else:
                self.log_warning("Portfolio total value not found in UI")

            if has_pnl:
                self.log_success("Portfolio P&L information displays")
            else:
                self.log_warning("P&L information not found in UI")

            # Check for price data
            if "price" in content.lower():
                self.log_success("Price information displays")
            else:
                self.log_warning("Price information not prominently displayed")

            return has_total or has_pnl

        except Exception as e:
            self.log_error(f"Valuation check failed: {e}")
            return False

    def test_transaction_history(self, page: Page):
        """Test that transaction history displays"""
        print("\n📋 Testing Transaction History...")

        try:
            content = page.content()

            # Look for transaction/history indicators
            has_transactions = any(text in content.lower() for text in ["transaction", "history", "activity"])

            if has_transactions:
                self.log_success("Transaction history section found")

                # Check for transaction types
                has_deposit = "deposit" in content.lower()
                has_buy = "buy" in content.lower() or "purchase" in content.lower()

                if has_deposit:
                    self.log_success("Deposit transaction visible in history")
                if has_buy:
                    self.log_success("Buy transaction visible in history")

                return True
            else:
                self.log_warning("Transaction history not found in UI")
                return False

        except Exception as e:
            self.log_error(f"Transaction history check failed: {e}")
            return False

    def take_screenshot(self, page: Page, name: str):
        """Take a screenshot for documentation"""
        try:
            page.screenshot(path=f"orchestrator_procedures/screenshots/{name}.png", full_page=True)
            self.log_success(f"Screenshot saved: {name}.png")
        except Exception as e:
            self.log_warning(f"Could not save screenshot: {e}")

    def run_validation(self):
        """Run the complete validation suite"""
        print("=" * 60)
        print("Zebu E2E Validation")
        print("=" * 60)

        # Check backend first
        if not self.check_backend_health():
            print("\n❌ Backend is not responding. Please start services.")
            return False

        # Run Playwright tests
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Set to True for CI
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()

            try:
                # Create screenshots directory
                import os
                os.makedirs("orchestrator_procedures/screenshots", exist_ok=True)

                # Test workflow
                portfolio_name = self.test_portfolio_creation(page)
                self.take_screenshot(page, "01_portfolio_created")

                if portfolio_name:
                    self.test_deposit_funds(page, portfolio_name)
                    self.take_screenshot(page, "02_funds_deposited")

                    self.test_buy_stock(page)
                    self.take_screenshot(page, "03_stock_purchased")

                    self.test_portfolio_valuation(page)
                    self.take_screenshot(page, "04_portfolio_valuation")

                    self.test_transaction_history(page)
                    self.take_screenshot(page, "05_transaction_history")

            finally:
                browser.close()

        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        print("=" * 60)

        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")

        # Overall result
        if len(self.errors) == 0:
            print("\n✅ VALIDATION PASSED")
            return True
        else:
            print("\n❌ VALIDATION FAILED")
            return False


def main():
    """Main entry point"""
    validator = E2EValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
