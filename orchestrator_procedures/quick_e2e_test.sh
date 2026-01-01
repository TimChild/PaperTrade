#!/bin/bash
# Quick E2E Test Script for PaperTrade
# Tests the complete workflow via API calls

set -e  # Exit on error

BASE_URL="http://localhost:8000/api/v1"
USER_ID="550e8400-e29b-41d4-a716-446655440000"

echo "============================================================"
echo "PAPERTRADE E2E API TESTING"
echo "============================================================"

# Test 1: Create Portfolio
echo ""
echo "📋 Test 1: Create Portfolio"
PORTFOLIO_RESPONSE=$(curl -s -X POST "$BASE_URL/portfolios" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"name": "E2E Test Portfolio", "description": "Automated test", "initial_deposit": 10000.00}')

PORTFOLIO_ID=$(echo $PORTFOLIO_RESPONSE | grep -o '"portfolio_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$PORTFOLIO_ID" ]; then
    echo "❌ Failed to create portfolio"
    echo "Response: $PORTFOLIO_RESPONSE"
    exit 1
fi

echo "✅ Portfolio created: $PORTFOLIO_ID"

# Test 2: Get Portfolio
echo ""
echo "📋 Test 2: Get Portfolio"
curl -s -X GET "$BASE_URL/portfolios/$PORTFOLIO_ID" \
  -H "X-User-Id: $USER_ID" | python3 -m json.tool

# Test 3: Buy Stock (AAPL)
echo ""
echo "📋 Test 3: Buy Stock (AAPL - 10 shares)"
echo "⏳ Fetching price from Alpha Vantage... (may take 1-2 seconds)"
BUY_RESPONSE=$(curl -s -X POST "$BASE_URL/portfolios/$PORTFOLIO_ID/trades" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"symbol": "AAPL", "shares": 10, "trade_type": "BUY"}')

echo "$BUY_RESPONSE" | python3 -m json.tool

# Check if buy was successful
if echo "$BUY_RESPONSE" | grep -q "transaction_id"; then
    echo "✅ Stock purchase successful"
else
    echo "❌ Stock purchase may have failed"
fi

# Test 4: Get Holdings
echo ""
echo "📋 Test 4: Get Holdings"
curl -s -X GET "$BASE_URL/portfolios/$PORTFOLIO_ID/holdings" \
  -H "X-User-Id: $USER_ID" | python3 -m json.tool

# Test 5: Get Transactions
echo ""
echo "📋 Test 5: Get Transaction History"
curl -s -X GET "$BASE_URL/portfolios/$PORTFOLIO_ID/transactions" \
  -H "X-User-Id: $USER_ID" | python3 -m json.tool

# Test 6: Sell Stock
echo ""
echo "📋 Test 6: Sell Stock (AAPL - 5 shares)"
SELL_RESPONSE=$(curl -s -X POST "$BASE_URL/portfolios/$PORTFOLIO_ID/trades" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"symbol": "AAPL", "shares": 5, "trade_type": "SELL"}')

echo "$SELL_RESPONSE" | python3 -m json.tool

if echo "$SELL_RESPONSE" | grep -q "transaction_id"; then
    echo "✅ Stock sale successful"
else
    echo "❌ Stock sale may have failed"
fi

# Test 7: Withdraw Funds
echo ""
echo "📋 Test 7: Withdraw Funds ($1000)"
WITHDRAW_RESPONSE=$(curl -s -X POST "$BASE_URL/portfolios/$PORTFOLIO_ID/withdraw" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"amount": 1000.00}')

echo "$WITHDRAW_RESPONSE" | python3 -m json.tool

# Test 8: Error Handling - Invalid Symbol
echo ""
echo "📋 Test 8: Error Handling (Invalid Symbol)"
INVALID_RESPONSE=$(curl -s -X POST "$BASE_URL/portfolios/$PORTFOLIO_ID/trades" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"symbol": "INVALID123", "shares": 1, "trade_type": "BUY"}')

if echo "$INVALID_RESPONSE" | grep -q "detail"; then
    echo "✅ Invalid symbol correctly rejected"
    echo "$INVALID_RESPONSE" | python3 -m json.tool
else
    echo "⚠️  WARNING: Invalid symbol may have been accepted!"
fi

# Test 9: Final Portfolio State
echo ""
echo "📋 Test 9: Final Portfolio State"
curl -s -X GET "$BASE_URL/portfolios/$PORTFOLIO_ID" \
  -H "X-User-Id: $USER_ID" | python3 -m json.tool

echo ""
echo "============================================================"
echo "E2E TESTING COMPLETE"
echo "============================================================"
echo "Portfolio ID: $PORTFOLIO_ID"
echo "You can view this portfolio in the frontend at:"
echo "http://localhost:5174"
