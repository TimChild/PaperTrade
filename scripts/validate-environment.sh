#!/usr/bin/env bash
# Environment Validation Script
# Checks that development environment is properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall success
ALL_CHECKS_PASSED=true

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
    ALL_CHECKS_PASSED=false
}

check_command() {
    local cmd=$1
    local required=${2:-true}

    if command -v "$cmd" &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -n1 || echo "unknown")
        print_success "$cmd: $version"
        return 0
    else
        if [ "$required" = true ]; then
            print_error "$cmd: NOT FOUND (required)"
            return 1
        else
            print_warning "$cmd: NOT FOUND (optional)"
            return 0
        fi
    fi
}

check_env_var() {
    local var_name=$1
    local required=${2:-false}
    local show_value=${3:-false}

    if [ -n "${!var_name}" ]; then
        if [ "$show_value" = true ]; then
            print_success "$var_name: ${!var_name}"
        else
            print_success "$var_name: SET"
        fi
        return 0
    else
        if [ "$required" = true ]; then
            print_error "$var_name: NOT SET (required)"
            return 1
        else
            print_warning "$var_name: NOT SET (optional)"
            return 0
        fi
    fi
}

check_docker_service() {
    local service=$1

    if docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
        print_success "Docker service '$service': Running"
        return 0
    else
        print_warning "Docker service '$service': Not running (start with 'task docker:up')"
        return 1
    fi
}

# Main validation
print_header "Environment Validation"
echo ""

# Check required tools
print_header "Required Tools"
check_command "uv" true
check_command "npm" true
check_command "task" true
check_command "docker" true
check_command "python3" true
check_command "node" true
check_command "git" true
echo ""

# Check optional tools
print_header "Optional Tools"
check_command "gh" false
check_command "pre-commit" false
check_command "playwright" false
echo ""

# Check Python/Node versions
print_header "Version Requirements"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
    print_success "Python $PYTHON_VERSION (>= 3.12 required)"
else
    print_error "Python $PYTHON_VERSION (>= 3.12 required, found $PYTHON_VERSION)"
fi

NODE_VERSION=$(node --version 2>&1 | grep -oE '[0-9]+' | head -1)
if [ "$NODE_VERSION" -ge 18 ]; then
    print_success "Node.js v$NODE_VERSION (>= 18 required)"
else
    print_error "Node.js v$NODE_VERSION (>= 18 required, found v$NODE_VERSION)"
fi
echo ""

# Check environment variables
print_header "Environment Variables"

# Check for .env file
if [ -f .env ]; then
    print_success ".env file exists"
    # Source it to check variables
    set -a
    source .env 2>/dev/null || true
    set +a
else
    print_warning ".env file not found (some features may not work)"
fi

# Required for E2E tests
check_env_var "CLERK_SECRET_KEY" false false
check_env_var "CLERK_PUBLISHABLE_KEY" false false
check_env_var "VITE_CLERK_PUBLISHABLE_KEY" false false
check_env_var "E2E_CLERK_USER_EMAIL" false true

# Optional
check_env_var "ALPHA_VANTAGE_API_KEY" false false
check_env_var "DATABASE_URL" false false
echo ""

# Check Docker services
print_header "Docker Services"
if docker compose ps > /dev/null 2>&1; then
    check_docker_service "db"
    check_docker_service "redis"
    check_docker_service "backend" || true  # Optional
    check_docker_service "frontend" || true  # Optional
else
    print_warning "Docker Compose not running (start with 'task docker:up')"
fi
echo ""

# Check project structure
print_header "Project Structure"
[ -d "backend" ] && print_success "backend/ directory exists" || print_error "backend/ directory missing"
[ -d "frontend" ] && print_success "frontend/ directory exists" || print_error "frontend/ directory missing"
[ -f "Taskfile.yml" ] && print_success "Taskfile.yml exists" || print_error "Taskfile.yml missing"
[ -f "docker-compose.yml" ] && print_success "docker-compose.yml exists" || print_error "docker-compose.yml missing"
echo ""

# Check dependencies installed
print_header "Dependencies"
if [ -d "backend/.venv" ] || [ -n "$(uv pip list 2>/dev/null)" ]; then
    print_success "Backend dependencies installed"
else
    print_warning "Backend dependencies not installed (run 'task setup:backend')"
fi

if [ -d "frontend/node_modules" ]; then
    print_success "Frontend dependencies installed"
else
    print_warning "Frontend dependencies not installed (run 'task setup:frontend')"
fi
echo ""

# Check Python imports (if backend is set up)
if [ -d "backend" ]; then
    print_header "Backend Health Check"
    cd backend
    if uv run python -c "import papertrade" 2>/dev/null; then
        print_success "Backend imports working"
    else
        print_warning "Backend imports failing (may need 'task setup:backend')"
    fi
    cd ..
    echo ""
fi

# Service health checks (if services are running)
print_header "Service Health"
if curl -f http://localhost:8000/health &> /dev/null; then
    print_success "Backend API: http://localhost:8000 (healthy)"
else
    print_warning "Backend API not responding (start with 'task docker:up:all' or 'task dev:backend')"
fi

if curl -f http://localhost:5173 &> /dev/null; then
    print_success "Frontend: http://localhost:5173 (healthy)"
else
    print_warning "Frontend not responding (start with 'task docker:up:all' or 'task dev:frontend')"
fi
echo ""

# Summary
print_header "Summary"
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}✓ All required checks passed!${NC}"
    echo ""
    echo "Your environment is ready for development."
    echo ""
    echo "Next steps:"
    echo "  - Run 'task test:all' to run all tests"
    echo "  - Run 'task docker:up:all' to start the full stack"
    echo "  - Run 'task dev:backend' and 'task dev:frontend' for development mode"
    exit 0
else
    echo -e "${RED}✗ Some required checks failed${NC}"
    echo ""
    echo "Please fix the errors above before proceeding."
    echo ""
    echo "Common fixes:"
    echo "  - Install tools: 'task setup'"
    echo "  - Start Docker: 'task docker:up'"
    echo "  - Install dependencies: 'task setup:backend' and 'task setup:frontend'"
    exit 1
fi
