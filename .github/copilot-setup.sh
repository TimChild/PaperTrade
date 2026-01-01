#!/bin/bash
# PaperTrade Development Environment Setup Script
#
# This script sets up a complete development environment for PaperTrade.
# It can be used by both human developers and Copilot agents.
#
# Usage: ./.github/copilot-setup.sh
#
# Requirements:
#   - Python 3.12+
#   - Node.js 20+
#   - Docker & Docker Compose

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
    echo "   uv not found, installing via pip..."
    python3 -m pip install --user uv
    export PATH="$HOME/.local/bin:$PATH"

    # Verify installation
    if command -v uv &> /dev/null; then
        echo "   ✓ uv installed successfully"
    else
        echo "   ⚠️  uv installed but not in PATH yet"
        echo "   Please add to your shell config (~/.bashrc or ~/.zshrc):"
        echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
else
    echo "   ✓ uv already installed"
fi

# 2. Create .env file if it doesn't exist
echo ""
echo "📝 Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ Created .env from .env.example"
    echo "   ⚠️  Remember to update ALPHA_VANTAGE_API_KEY in .env for market data features"
else
    echo "   ✓ .env already exists"
fi

# 3. Install pre-commit
echo ""
echo "📋 Installing pre-commit hooks..."
if ! command -v pre-commit &> /dev/null; then
    echo "   pre-commit not found, installing with uv..."
    uv tool install pre-commit
fi
uv tool run pre-commit install
uv tool run pre-commit install --hook-type pre-push

# Verify pre-commit hooks installation
if [ -f ".git/hooks/pre-push" ]; then
    echo "   ✓ Pre-commit hooks installed and verified"
else
    echo "   ⚠️  WARNING: Pre-commit hooks may not be installed correctly"
fi

# 4. Backend setup
echo ""
echo "🐍 Setting up backend (Python + uv)..."
cd backend
uv sync --all-extras
echo "   ✓ Backend dependencies installed"
cd ..

# 5. Frontend setup
echo ""
echo "⚛️  Setting up frontend (Node + npm)..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    # Check for node_modules in the correct directory (frontend/)
    if [ -f "node_modules/.package-lock.json" ]; then
        echo "   Frontend dependencies already installed, skipping..."
    else
        npm ci
        echo "   ✓ Frontend dependencies installed"
    fi
    cd ..
else
    echo "   ⚠️  Frontend not found, skipping..."
fi

# 6. Docker services
echo ""
echo "🐳 Starting Docker services (PostgreSQL + Redis)..."
if command -v docker compose &> /dev/null; then
    docker compose up -d

    # Give services a moment to start
    echo "   Waiting for services to be healthy..."
    sleep 3

    # Check if services are running
    if docker compose ps | grep -q "Up"; then
        echo "   ✓ Docker services are running"
        echo "      - PostgreSQL: localhost:5432"
        echo "      - Redis: localhost:6379"
    else
        echo "   ⚠️  WARNING: Docker services may not be healthy"
        docker compose ps
    fi
else
    echo "   ⚠️  Docker Compose not found, skipping..."
    echo "      You'll need to start services manually: docker compose up -d"
fi

# 7. Validation
echo ""
echo "🔍 Validating setup..."

# Test backend can import
cd backend
if uv run python -c "import papertrade" 2>/dev/null; then
    echo "   ✓ Backend imports work"
else
    echo "   ⚠️  WARNING: Backend imports failed (may need to configure database)"
fi
cd ..

# Test frontend dependencies
if [ -f "frontend/node_modules/.package-lock.json" ]; then
    echo "   ✓ Frontend dependencies verified"
else
    echo "   ⚠️  WARNING: Frontend dependencies verification failed"
fi

# 8. Summary
echo ""
echo "✅ Setup complete!"
echo ""

# Important PATH note if tools were installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  IMPORTANT: To use newly installed tools, run:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "   Or add this line to your ~/.bashrc or ~/.zshrc for persistence."
    echo ""
fi

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
