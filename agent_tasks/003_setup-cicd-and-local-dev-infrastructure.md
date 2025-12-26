# Task 003: Setup CI/CD Pipeline and Local Development Infrastructure

## Objective
Create GitHub Actions workflows for CI, Docker Compose for local development, Taskfile for command orchestration, and pre-commit hooks.

## Context
This is Phase 0 work - establishing the foundation. The backend scaffolding (Task 001) has been merged, and frontend (Task 002) is in progress. This task sets up the infrastructure to validate code quality and enable consistent local development.

## Requirements

### GitHub Actions Workflows

#### PR Workflow (`.github/workflows/pr.yml`)
Runs on all pull requests:
```yaml
jobs:
  backend-quality:
    - Checkout code
    - Setup Python 3.13 with uv
    - Install dependencies
    - Run ruff check
    - Run pyright
    - Run pytest with coverage
    
  frontend-quality:
    - Checkout code  
    - Setup Node.js 20
    - Install dependencies
    - Run eslint
    - Run typecheck (tsc)
    - Run vitest
    - Run build check
```

#### Main Branch Workflow (`.github/workflows/main.yml`)
Runs on pushes to main:
- All PR checks plus any additional validation
- Could include build artifacts in future

### Docker Compose (`docker-compose.yml`)
For local development, create services for:
```yaml
services:
  db:
    image: postgres:16
    environment variables for dev
    volume for data persistence
    healthcheck
    
  redis:
    image: redis:7-alpine
    healthcheck
    
  # Backend and frontend services can be added later
  # when we have proper Dockerfiles
```

### Taskfile (`Taskfile.yml`)
Command orchestration with tasks:
```yaml
tasks:
  setup:
    desc: "Set up complete development environment"
    # Install backend deps, frontend deps, start docker services
    
  dev:
    desc: "Start development servers"
    # Start docker services, backend, frontend
    
  dev:backend:
    desc: "Start backend development server"
    
  dev:frontend:
    desc: "Start frontend development server"
    
  test:
    desc: "Run all tests"
    
  test:backend:
    desc: "Run backend tests"
    
  test:frontend:
    desc: "Run frontend tests"
    
  lint:
    desc: "Run all linters"
    
  lint:backend:
    desc: "Run backend linters (ruff, pyright)"
    
  lint:frontend:
    desc: "Run frontend linters (eslint, tsc)"
    
  docker:up:
    desc: "Start Docker services"
    
  docker:down:
    desc: "Stop Docker services"
    
  clean:
    desc: "Clean build artifacts and caches"
```

### Pre-commit Configuration (`.pre-commit-config.yaml`)
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - trailing-whitespace
      - end-of-file-fixer
      - check-yaml
      - check-added-large-files
      
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - ruff (lint)
      - ruff-format
      
  - repo: local
    hooks:
      - pyright (backend)
      - eslint (frontend) - optional, can be slow
```

### Environment Configuration
- `.env.example` - Template for environment variables
- Document required environment variables in README

## Success Criteria
- [ ] PR workflow runs and passes on new PRs
- [ ] `docker compose up -d` starts postgres and redis
- [ ] `task setup` installs all dependencies
- [ ] `task lint` runs all linters
- [ ] `task test` runs all tests
- [ ] `pre-commit run --all-files` passes
- [ ] GitHub Actions badge can be added to README

## Dependencies
- Backend scaffolding (Task 001) - MERGED
- Frontend scaffolding (Task 002) - IN PROGRESS (workflow should handle if frontend dir doesn't exist yet)

## References
- See `.github/agents/quality-infra.md` for standards
- See `project_strategy.md` for infrastructure decisions
- See `.github/copilot-instructions.md` for general guidelines

## Notes
- Make workflows resilient - skip frontend checks if frontend dir doesn't exist
- Use caching in GitHub Actions for faster runs (uv cache, npm cache)
- Keep Docker Compose minimal for now - just db and redis
- Taskfile should work on macOS and Linux
