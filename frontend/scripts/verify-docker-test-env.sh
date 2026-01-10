#!/bin/bash
# Script to verify Docker test environment is correctly configured

set -e

echo "=========================================="
echo "Docker Test Environment Verification"
echo "=========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

echo "✅ Docker is available"

# Check if docker-compose is available
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
fi

echo "✅ Docker Compose is available"

# Validate docker-compose.yml
echo ""
echo "Validating docker-compose.yml..."
if docker compose -f ../../docker-compose.yml config --quiet 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    exit 1
fi

# Check that required files exist
echo ""
echo "Checking required files..."

FILES=(
    "vitest.config.ts"
    "tests/setup.ts"
    "package.json"
)

for file in "${FILES[@]}"; do
    if [ -f "../${file}" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

# Check if tests directory exists
if [ -d "../tests" ]; then
    echo "✅ tests directory exists"
else
    echo "❌ tests directory is missing"
    exit 1
fi

# Count all test files
TEST_COUNT=$(find .. -name "*.test.ts" -o -name "*.test.tsx" 2>/dev/null | wc -l)
echo "✅ Found $TEST_COUNT test files in project"

echo ""
echo "=========================================="
echo "Pre-flight checks complete!"
echo "=========================================="
echo ""
echo "To run tests in Docker:"
echo "1. Build and start the frontend container:"
echo "   docker compose up -d frontend"
echo ""
echo "2. Run tests inside the container:"
echo "   docker compose exec frontend npm run test:unit"
echo ""
echo "Expected result: All 194 tests should pass"
echo "=========================================="
