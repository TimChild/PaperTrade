# CI Infrastructure Audit — Phase B1

- **Auditor**: `quality-infra`
- **Slug**: `ci`
- **Date**: 2026-05-09
- **Scope**: `.github/workflows/`, `.pre-commit-config.yaml`, `Taskfile.yml` CI surface
- **Source files reviewed**:
  - `.github/workflows/ci.yml`
  - `.github/workflows/cd.yml`
  - `.github/workflows/copilot-setup-steps.yml`
  - `.github/workflows/docs.yml`
  - `.github/workflows/test-runner.yml`
  - `.github/workflows/README.md`
  - `.pre-commit-config.yaml`
  - `Taskfile.yml` (`ci`, `quality:*`, `validate:*`, `health:*`, `test:*`)

## Summary

| P | Count |
|---|------:|
| P0 | 1 |
| P1 | 4 |
| P2 | 3 |
| P3 | 2 |

Top concern: **`ci.yml` has no concurrency-cancellation block, so every PR push spins up a fresh full pipeline (including the heavy E2E job that builds Docker, installs Playwright, and pulls Clerk) while older runs keep burning minutes.** With agents pushing commits in tight loops this is a direct, measurable feedback-time tax — and it's a one-line fix.

**Self-hosted runner verdict**: Probably paying off for CD, but currently unused by CI. The runner is _only_ wired into `cd.yml` and a manual `test-runner.yml`. The CI job (`ci.yml`) — the one agents wait on — runs on `ubuntu-latest`. There's also no cleanup/disk-prune step on the runner, no documented timeout/concurrency limits beyond the workflow-level `timeout-minutes: 15` on CD, and the runner's stdout is plain `echo` lines without structured timestamps or grep-friendly job markers. Net: it's adequate for a single deploy at a time, but it isn't being leveraged where it would actually move the needle (CI feedback for agents) and its log output is no more agent-friendly than ubuntu-latest.

---

## Findings

### CI-P0-1 — No concurrency cancellation on `ci.yml`

**File**: `.github/workflows/ci.yml` lines 1-15

`ci.yml` triggers on every PR `synchronize` and every `push` to `main` but has zero `concurrency:` block. Two consecutive PR pushes (or a force-push during agent loops) currently run **every** previous pipeline to completion, including the expensive `e2e-tests` job that does `npx playwright install --with-deps`, builds the full Docker stack, and exercises Clerk. CD (`cd.yml`) and docs (`docs.yml`) both have correct `concurrency:` blocks; CI does not.

For agent-driven work this is a P0 — a 30-minute backlog of stale runs blocks decision-making and consumes Codecov/GitHub-Actions budget for runs whose results no one will read.

**Fix** (3 lines): add to `ci.yml` after the `on:` block:

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

The `github.ref != 'refs/heads/main'` clause keeps `main` runs serialized (don't cancel a deploy-eligible run); PR runs cancel freely. This is the standard pattern in `cd.yml` already.

---

### CI-P1-1 — Self-hosted runner is not used by CI; cleanup/disk discipline is absent

**Files**: `.github/workflows/ci.yml` (uses `ubuntu-latest` for all three jobs), `cd.yml` (uses `[self-hosted, proxmox]`), `scripts/proxmox-vm/` (no prune helpers)

The proposal calls out that `papertrade-proxmox` should be "materially faster than GitHub-hosted" and "logs genuinely useful for agent debugging." Today:

1. **Runner only used by CD + a manual smoke test.** The actual feedback-loop workflow (`ci.yml`) runs on hosted ubuntu, so the self-hosted runner contributes _zero_ to the speed agents perceive when iterating on PRs.
2. **No automated docker/disk cleanup.** `cd.yml` does `docker compose build/up` repeatedly on the same VM with no `docker system prune` or volume cleanup at the end. The runner's disk will eventually fill — at which point CI fails with cryptic "no space left on device" errors that look exactly like flakiness. Task #097/`scripts/proxmox-vm/` has no prune helper either.
3. **No structured logging.** Steps emit plain `echo "  ✅ Backend ready"` style output with leading spaces and emojis. For agent log-parsing this is hostile — there's no grepable run-id, step boundaries, or machine-readable status lines.

**Fix recommendations** (in priority order):

- Move backend-checks + frontend-checks to `[self-hosted, proxmox]` _only after_ Phase B has stabilized auth (otherwise we trade GitHub flakes for runner-disk flakes). Keep `e2e-tests` hosted until parallel-PR isolation is solved (the runner can't run two concurrent E2E stacks against the same docker-compose project name without colliding ports).
- Add a `post-deploy` step in `cd.yml`: `docker image prune -af --filter "until=72h"` and `docker volume prune -f`. Cheap insurance.
- Wrap each step's logical chunks in `::group::` / `::endgroup::` markers (GitHub Actions native log folding) and emit a single `STATUS=ok|fail STEP=<name>` trailer line per major step so an agent can tail the log.

---

### CI-P1-2 — uv cache key is missing the Python version and is duplicated across three workflows

**Files**: `ci.yml` lines 35-42, 141-147; `copilot-setup-steps.yml` lines 64-70

The cache key is `${{ runner.os }}-uv-${{ hashFiles('backend/uv.lock') }}` everywhere. Two issues:

1. **No Python version in the key.** When the project bumps from 3.13 → 3.14, the cache will be silently restored with wheels built for the wrong interpreter. uv tolerates this often but not always (wheels with C extensions, e.g. `pydantic-core`, blow up).
2. **Duplicated three times verbatim.** Three workflows each maintain their own copy. Drift is inevitable — and agents touching the file are likely to update one and miss the others.

**Fix**:

- Use the cache built into `astral-sh/setup-uv@v4` directly (it ships an `enable-cache: true` input as of v4) instead of hand-rolled `actions/cache`. This single change removes ~7 lines per workflow and gets the python version, OS, arch, and lock file mixed into the key automatically.
- Or, if keeping manual cache: add `${{ env.pythonLocation }}` to the key.

---

### CI-P1-3 — E2E job duplicates 4 setup steps that already ran in `backend-checks` / `frontend-checks`

**File**: `.github/workflows/ci.yml` lines 115-163

`e2e-tests` declares `needs: [backend-checks, frontend-checks]` but then re-runs:

- checkout (necessary)
- setup-python + install uv (~30s)
- setup-node (~10s)
- restore uv cache + `task setup:backend` (~60-120s on cache miss)
- `task setup:frontend` (~30-60s)

That's 2-4 minutes of duplicated setup _per PR_ that agents wait on. Options:

1. **Build a Docker image in `backend-checks`/`frontend-checks` and pull it in `e2e-tests`.** Highest leverage but requires GHCR setup.
2. **Use `actions/upload-artifact` to ship the installed `.venv` and `node_modules` from the earlier jobs.** Cheap; works today.
3. **Run e2e on the same job as one of the others.** Loses the parallelism, but if E2E is the long pole it might net positive.

**Recommendation**: option 2, gated on cache size (artifacts above ~1GB will themselves be slow to upload — measure first).

---

### CI-P1-4 — `[skip deploy]` is fragile: only checks `head_commit.message`, breaks for squash-merges and `workflow_dispatch`

**File**: `.github/workflows/cd.yml` line 19

```yaml
if: "!contains(github.event.head_commit.message, '[skip deploy]')"
```

Three failure modes:

1. **Squash-merge PRs**: `head_commit.message` is the squash-commit body, which (depending on GitHub UI flow) may or may not include the original `[skip deploy]` token. If a contributor adds `[skip deploy]` only in PR description, it's silently ignored.
2. **`workflow_dispatch`**: when manually triggering, `head_commit` may be `null` and `contains(null, ...)` evaluates to `false`, so `!contains(...)` becomes `true` — the deploy proceeds. That's actually the desired behavior here, but it's accidental, not designed.
3. **PR-merge commits**: the `head_commit.message` for a merge commit is "Merge pull request #N…" — won't contain the token even if every PR commit had it.

**Fix**: also check `github.event.commits` (the array — for push events with multiple commits) or, more robustly, switch to a label-based skip (`if: !contains(github.event.pull_request.labels.*.name, 'skip-deploy')` — though this only applies to PR-trigger workflows; for push-to-main, the message check is the only option).

This is P1 not P0 because the current wording works for the most common case (single-commit pushes to main with the token in the message), but agents hitting the corner cases will see "I added `[skip deploy]` and it deployed anyway" flakiness.

---

### CI-P2-1 — `npm audit` set to `continue-on-error: true` with no actionable output

**File**: `.github/workflows/ci.yml` lines 101-104

```yaml
- name: Security audit
  run: npm audit --audit-level=moderate
  working-directory: ./frontend
  continue-on-error: true
```

`continue-on-error: true` plus no artifact upload means the audit log only lives in GitHub UI logs for ~90 days and there's no trigger when a new vuln appears. Either gate merges on it (and pin/ignore false-positives in `npm audit --audit-level=high`) or remove it — the current state is "warm-fuzzy theater."

---

### CI-P2-2 — Pyright runs in pre-commit pre-push, in `task quality:backend` (CI), and on every developer push — three full type-checks per change

**Files**: `.pre-commit-config.yaml` lines 70-77; `Taskfile.yml` lines 442-448

Pyright is the slowest pre-push hook (~20-40s on this codebase) and it runs again identically inside `task quality:backend` once the PR opens. Running pyright in pre-commit catches some breakages locally before push but mostly costs every developer 20-40s on each push that they could otherwise spend iterating. Suggest:

- Drop pyright from pre-push (keep it as a `task lint:backend` opt-in for those who want it).
- Or: run pyright in pre-push with `--outputjson` redirected, only fail if the diff between local and base introduced new issues. Probably overkill.

---

### CI-P2-3 — `health:wait` and `cd.yml` waits use `timeout 60` with `sleep 2` — a 30-iter retry loop

**Files**: `Taskfile.yml` lines 604-628; `.github/workflows/cd.yml` lines 53-77

Backend health-check loop allows max 30 retries × 2s = 60s. With cold uv installs and Alembic migrations on production, 60s for the backend can be tight. We've already seen migration-related flakiness in the recent commit log (`4d7b313 fix: support async DB driver in alembic`). Recommend bumping backend wait to 120s, frontend to 90s, with progress-line emission every 10s to make it obvious what's hanging.

---

### CI-P3-1 — `docs.yml` `paths:` filter only triggers on `docs/**` and `mkdocs.yml`; doesn't trigger on `.github/workflows/docs.yml`

**File**: `.github/workflows/docs.yml` lines 5-10

If someone updates the docs workflow itself, it won't run on the change to validate. Add `.github/workflows/docs.yml` to the `paths:` list. Trivial.

---

### CI-P3-2 — `test-runner.yml` is a 5-line manual smoke test with no purpose stated

**File**: `.github/workflows/test-runner.yml`

```yaml
name: Test Self-Hosted Runner
on: workflow_dispatch
jobs:
  test:
    runs-on: [self-hosted, proxmox]
    steps:
      - uses: actions/checkout@v4
      - run: echo "Hello from $(hostname)!"
      - run: docker ps
      - run: task --version
```

No `name:` on steps, no docs comment explaining when to run it, no failure mode. Either:

- Delete it (the same thing can be done with `gh workflow run` + ad-hoc),
- Or expand it into a real "is the runner healthy" diagnostic (df -h, docker system df, runner version) and document it in the workflows README.

Defer to P3 because it's a one-off; doesn't burn cycles.

---

## Things that are healthy and don't need changes

- Pre-commit pre-push design (avoiding the double-commit problem) — well-thought-out.
- `cd.yml` concurrency block is correct (`group: production-deploy`, `cancel-in-progress: false`).
- Action versions pinned to majors uniformly (`@v4`, `@v5`, etc.) — consistent.
- Codecov has `fail_ci_if_error: false` — coverage outage doesn't break PRs.
- Secrets are referenced via `secrets.X` consistently; no embedded keys, no `set-output`, no `printenv` of secrets in logs.
- The `.env`-creation step in `copilot-setup-steps.yml` writes secrets to a file under the workflow workspace — that file isn't uploaded as an artifact, isn't echoed, and is wiped at the end of the run. Acceptable.
- `arduino/setup-task@v2` use is uniform; Task is the right abstraction layer for "same commands locally and in CI."

## Hypothesis on the self-hosted runner

**It is paying off in the narrow sense — CD on `main` runs reliably, the production `.env` doesn't have to leave the VM, and concurrency is enforced. But it is not paying off in the way the agent-platform proposal needs.** The agent-perceivable speed-up is determined by `ci.yml`, which is on hosted ubuntu. Moving CI to the runner would likely cut 1-2 minutes per run (no GitHub-side runner allocation, hot uv/npm caches on local SSD), but only after we add (a) auto-cleanup, (b) workspace-isolation between concurrent CI runs (separate `COMPOSE_PROJECT_NAME` per job), and (c) structured log markers. Without those three, putting CI on the runner trades ~90s flakiness for disk-fill flakiness — net negative.

Recommended sequencing: ship CI-P0-1 and CI-P1-2 immediately (pure wins, no runner involvement), then defer the "move CI to self-hosted" work until B1 wraps and we can budget the runner-hardening sprint properly.
