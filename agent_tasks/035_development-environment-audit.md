# Task 035: Development Environment Audit

**Created**: January 1, 2026
**Priority**: P1 - HIGH (critical for developer/agent onboarding)
**Estimated Effort**: 2-3 hours
**Status**: AUDIT COMPLETE - Action Required

## Executive Summary

Comprehensive audit of PaperTrade's development environment setup procedures, tooling, and documentation. Identified **8 critical issues** and **5 moderate issues** that impact the ability to set up a working development environment.

**Critical Finding**: The `.github/copilot-setup.sh` script **fails completely** in restricted network environments (like GitHub Actions runners) due to inability to download tools from external URLs.

## Audit Methodology

1. ✅ Reviewed all setup documentation (README.md, copilot-instructions.md)
2. ✅ Executed setup scripts (`copilot-setup.sh`)
3. ✅ Tested Task commands
4. ✅ Verified Docker configuration
5. ✅ Checked dependency management files
6. ✅ Reviewed CI/CD workflows
7. ✅ Tested pre-commit hooks
8. ✅ Verified all required tools

## Test Environment

- **OS**: Ubuntu 22.04 (GitHub Actions runner environment)
- **Python**: 3.12.3 (System version)
- **Node.js**: v20.19.6  ✅
- **npm**: 10.8.2  ✅
- **Docker**: 28.0.4  ✅
- **Docker Compose**: v2.38.2  ✅

## Findings

### 🔴 CRITICAL ISSUES

#### 1. Network-Dependent Setup Script Fails
**File**: `.github/copilot-setup.sh`
**Severity**: CRITICAL
**Impact**: Setup completely fails in GitHub Actions or restricted networks

**Problem**:
```bash
# Line 31: Downloads uv installer from external URL
curl -LsSf https://astral.sh/uv/install.sh | sh
# ❌ FAILS: "Could not resolve host: astral.sh"
```

**Root Cause**: GitHub Actions runners and many CI environments block external downloads

**Evidence**:
```
curl: (6) Could not resolve host: astral.sh
./.github/copilot-setup.sh: line 43: uv: command not found
```

**Workaround Found**:
```bash
# Alternative that works:
python3 -m pip install --user uv
# ✅ SUCCESS: uv installed via PyPI
```

**Recommendation**: 
- Primary: Use `pip install uv` (doesn't require curl)
- Fallback: Keep curl method as alternative
- Add proper error handling and retry logic

---

#### 2. Missing .env File Creation
**Severity**: CRITICAL
**Impact**: Application fails to start without .env file

**Problem**:
- README says "Copy environment variables template: `cp .env.example .env`"
- Setup scripts DON'T create .env file automatically
- New developers/agents will forget this step

**Current State**:
- ✅ `.env.example` exists
- ❌ `.env` does NOT exist after running setup
- ❌ No validation that .env was created

**Recommendation**:
Add to setup script:
```bash
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ Created .env from .env.example"
fi
```

---

#### 3. Python Version Inconsistency
**Severity**: HIGH
**Impact**: Confusion about minimum Python version, potential compatibility issues

**Inconsistencies Found**:

| Location | Version Required |
|----------|------------------|
| README.md | "Python 3.13+" |
| backend/pyproject.toml | ">=3.12" |
| .github/workflows/ci.yml | "3.13" (exact) |
| .github/workflows/copilot-setup.yml | "3.13" (exact) |
| System Available | 3.12.3 |

**Problem**: 
- README says 3.13+ is required
- pyproject.toml allows 3.12+
- Test environment has 3.12.3
- Will setup work or not? Unclear!

**Recommendation**: 
Pick ONE version and update all locations:
- **Option A**: Require 3.12+ everywhere (most compatible)
- **Option B**: Require 3.13+ everywhere (as per README)

**If choosing 3.12+**:
- Update README.md: s/3.13+/3.12+/
- Keep pyproject.toml as-is
- Update CI workflows to use 3.12 for compatibility testing

**If choosing 3.13+**:
- Update pyproject.toml: s/>=3.12/>=3.13/
- Keep README as-is
- Ensure all environments have 3.13+

---

#### 4. Task Runner Not Installed by Setup Script
**Severity**: HIGH
**Impact**: All `task` commands in README fail

**Problem**:
- README prominently features Task commands: `task setup`, `task dev`, etc.
- copilot-setup.sh does NOT install Task
- Users follow README → commands fail → confusion

**Current State**:
```bash
$ task setup
bash: task: command not found  ❌
```

**Workaround**: 
- Manual install required
- Or use npm/uv commands directly
- But README doesn't explain this

**Recommendation**:
Either:
1. **Install Task in setup script** (preferred):
   ```bash
   sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d ~/.local/bin
   ```
2. **OR remove Task dependency**:
   - Make Task optional
   - Document both "with Task" and "without Task" workflows
   - Show equivalent commands

---

#### 5. Setup Script Doesn't Update PATH
**Severity**: HIGH
**Impact**: Newly installed tools not accessible

**Problem**:
After installing uv, the script says:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

But this only affects the script's shell session, not the user's terminal!

**Result**:
```bash
# After script completes:
$ uv --version
bash: uv: command not found  ❌
```

**Recommendation**:
Add to setup script:
```bash
echo ""
echo "⚠️  IMPORTANT: Add to your ~/.bashrc or ~/.zshrc:"
echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "Or run now: export PATH=\"\$HOME/.local/bin:\$PATH\""
```

---

### 🟡 MODERATE ISSUES

#### 6. Pre-commit Hooks Not Verified
**Severity**: MODERATE
**Impact**: Hooks may not work as expected, formatting inconsistencies

**Problem**:
- setup script installs pre-commit
- But doesn't verify installation succeeded
- Doesn't test hooks work

**Current**:
```bash
uv tool run pre-commit install
# No verification that this worked
```

**Recommendation**:
```bash
uv tool run pre-commit install
uv tool run pre-commit install --hook-type pre-push
# Verify
if [ -f ".git/hooks/pre-push" ]; then
    echo "   ✓ Pre-commit hooks verified"
else
    echo "   ❌ WARNING: Pre-commit hooks failed to install"
fi
```

---

#### 7. Docker Services Not Health-Checked
**Severity**: MODERATE
**Impact**: Services may be starting but not healthy

**Problem**:
```bash
docker compose up -d
echo "   ✓ Docker services started"
```

Services might be "started" but not healthy (PostgreSQL not accepting connections yet)

**Recommendation**:
Add health check:
```bash
docker compose up -d
echo "   Waiting for services to be healthy..."
sleep 5
if docker compose ps | grep -q "healthy\|Up"; then
    echo "   ✓ Docker services are running"
else
    echo "   ⚠️  WARNING: Docker services may not be healthy"
    docker compose ps
fi
```

---

#### 8. Frontend Dependencies Skip Logic Wrong
**Severity**: MODERATE
**Impact**: Frontend setup skipped even when it should run

**Problem**:
```bash
if [ -d "node_modules" ]; then
    echo "   Frontend dependencies already installed, skipping..."
else
    npm ci
fi
```

This checks for `node_modules` in the WRONG directory (repo root instead of frontend/)

**Recommendation**:
```bash
cd frontend
if [ -d "node_modules" ]; then
    echo "   Frontend dependencies already installed, skipping..."
else
    npm ci
    echo "   ✓ Frontend dependencies installed"
fi
cd ..
```

---

#### 9. No Validation of Successful Setup
**Severity**: MODERATE
**Impact**: Setup might fail silently

**Problem**:
- Script reports "✅ Setup complete!" even if steps failed
- No smoke tests to verify environment works

**Recommendation**:
Add validation section:
```bash
echo ""
echo "🔍 Validating setup..."

# Test backend can import
cd backend
if uv run python -c "import papertrade" 2>/dev/null; then
    echo "   ✓ Backend imports work"
else
    echo "   ❌ Backend imports FAILED"
    exit 1
fi
cd ..

# Test frontend dependencies
if [ -f "frontend/node_modules/.package-lock.json" ]; then
    echo "   ✓ Frontend dependencies verified"
else
    echo "   ❌ Frontend dependencies FAILED"
    exit 1
fi

echo "✅ Setup validation passed!"
```

---

#### 10. Missing Task Installation Check
**Severity**: MODERATE
**Impact**: Users don't know if Task is available

**Problem**:
README assumes Task is installed, but provides no way to check or install it

**Recommendation**:
Add to README:
```markdown
### Install Task (Optional but Recommended)

Task is used for development commands. Install it:

**macOS/Linux**:
```bash
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d ~/.local/bin
```

**Or use npm**:
```bash
npm install -g @go-task/cli
```

**Verify**:
```bash
task --version
```

**Alternative**: All `task` commands can be run manually (see Taskfile.yml)
```

---

### ✅ WORKING CORRECTLY

1. ✅ All required project files exist
2. ✅ docker-compose.yml is valid
3. ✅ backend/pyproject.toml is present and valid
4. ✅ frontend/package.json is present and valid
5. ✅ .pre-commit-config.yaml is present
6. ✅ CI workflows exist and are syntactically valid
7. ✅ Python version available (3.12.3) meets minimum requirement (3.12+)
8. ✅ Node.js version (20.19.6) meets requirement (20+)
9. ✅ Docker and Docker Compose are available

---

## Recommendations Summary

### Priority 1 (Fix Immediately)

1. **Fix setup script network dependency** - Use `pip install uv` instead of curl
2. **Auto-create .env file** - Copy from .env.example
3. **Resolve Python version inconsistency** - Decide 3.12 or 3.13
4. **Install Task in setup script** - Or document it's optional
5. **Fix PATH export instructions** - Tell users to update shell config

### Priority 2 (Fix Soon)

6. Verify pre-commit hooks installation
7. Health-check Docker services
8. Fix frontend directory check
9. Add setup validation tests
10. Document Task installation

### Priority 3 (Nice to Have)

11. Add retry logic for network operations
12. Create devcontainer.json for Codespaces
13. Add `task doctor` command to diagnose issues
14. Create troubleshooting guide

---

## Proposed Implementation

### Phase 1: Fix Critical Issues (Priority 1)

**Files to Modify**:
- `.github/copilot-setup.sh` - Fix uv installation, add .env creation, fix PATH, verify tools
- `README.md` - Fix Python version to 3.12+
- `backend/pyproject.toml` - (Keep as-is with >=3.12)

**Changes to copilot-setup.sh**:

1. Replace curl-based uv installation with pip
2. Add .env file creation
3. Fix frontend node_modules check directory
4. Add PATH setup instructions
5. Add verification steps

### Phase 2: Improve Reliability (Priority 2)

**Files to Modify**:
- `.github/copilot-setup.sh` - Add verification and health checks

**Changes**:
1. Verify pre-commit hooks installation
2. Health-check Docker services
3. Add setup validation tests

### Phase 3: Documentation (Priority 3)

**Files to Modify**:
- `README.md` - Add Task installation section
- Create `docs/TROUBLESHOOTING.md` (optional)

---

## Testing Plan

1. Test in fresh Ubuntu container
2. Run modified setup script
3. Verify:
   - uv installs successfully
   - .env file is created
   - PATH instructions are clear
   - All tools are accessible
   - Backend can be run
   - Frontend can be run
   - Tests pass

---

## Success Criteria

- [ ] Setup script works in restricted network environment (GitHub Actions)
- [ ] All tools install successfully without manual intervention
- [ ] .env file is created automatically
- [ ] Python version requirement is consistent across all files
- [ ] PATH setup instructions are clear
- [ ] Setup validation confirms environment is working
- [ ] Documentation matches actual behavior
- [ ] All `task` commands work OR are clearly documented as optional

---

## Files to Change

### Must Change (Phase 1)
- `.github/copilot-setup.sh` - Fix critical setup issues
- `README.md` - Fix Python version inconsistency

### Should Change (Phase 2)
- `.github/copilot-setup.sh` - Add verification and validation

### Nice to Change (Phase 3)
- `README.md` - Add Task installation documentation
- Create `docs/TROUBLESHOOTING.md` - Help users debug issues

---

**Estimated time to fix Priority 1 issues**: 1-2 hours
**Estimated time to fix all issues**: 3-4 hours
