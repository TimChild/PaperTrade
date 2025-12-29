#!/bin/bash
# PaperTrade Development Environment Setup Script
#
# This script sets up a complete development environment for PaperTrade.
# It can be used by both human developers and Copilot agents.
#
# Usage: ./.github/copilot-setup.sh
#
# Requirements:
#   - Python 3.13+
#   - Node.js 20+
#   - Docker & Docker Compose
#   - curl (for uv installation)

set -e  # Exit on error

echo "🚀 Setting up PaperTrade development environment..."
echo ""

# Check if we're in the repository root
if [ ! -f "README.md" ] || [ ! -d "backend" ]; then
    echo "❌ Error: This script must be run from the repository root."
    echo "   Current directory: $(pwd)"
    exit 1
fi

# 1. Install uv if not already installed
echo "📦 Checking for uv (Python package manager)..."
if ! command -v uv &> /dev/null; then
    echo "   uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "   ✓ uv installed"
else
    echo "   ✓ uv already installed"
fi

# 2. Install pre-commit
echo ""
echo "📋 Installing pre-commit hooks..."
if ! command -v pre-commit &> /dev/null; then
    echo "   pre-commit not found, installing with uv..."
    uv tool install pre-commit
fi
uv tool run pre-commit install
uv tool run pre-commit install --hook-type pre-push
echo "   ✓ Pre-commit hooks installed"

# 3. Backend setup
echo ""
echo "🐍 Setting up backend (Python + uv)..."
cd backend
uv sync --all-extras
echo "   ✓ Backend dependencies installed"
cd ..

# 4. Frontend setup
echo ""
echo "⚛️  Setting up frontend (Node + npm)..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    if [ -d "node_modules" ]; then
        echo "   Frontend dependencies already installed, skipping..."
    else
        npm ci
        echo "   ✓ Frontend dependencies installed"
    fi
    cd ..
else
    echo "   ⚠️  Frontend not found, skipping..."
fi

# 5. Docker services
echo ""
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
if command -v docker compose &> /dev/null; then
    docker compose up -d
    echo "   ✓ Docker services started"
    echo "      - PostgreSQL: localhost:5432"
    echo "      - Redis: localhost:6379"
else
    echo "   ⚠️  Docker Compose not found, skipping..."
    echo "      You'll need to start services manually: docker compose up -d"
fi

# 6. Summary
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  - Backend: cd backend && uv run uvicorn papertrade.main:app --reload"
echo "  - Frontend: cd frontend && npm run dev"
echo "  - Tests: cd backend && uv run pytest"
echo ""
echo "Or use Taskfile commands (if you have Task installed):"
echo "  - task dev:backend   # Start backend dev server"
echo "  - task dev:frontend  # Start frontend dev server"
echo "  - task test          # Run all tests"
echo ""
echo "Pre-commit hooks are configured to run on push (not commit)."
echo "This prevents the 'double commit' problem with auto-formatters."
echo "To skip hooks: git push --no-verify"
