# Dependencies Audit — Phase B1

**Date**: 2026-05-09
**Auditor**: quality-infra
**Slug**: deps
**Scope**: `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`, `frontend/package-lock.json`. Tooling: `npm audit`, `uv pip list --outdated`, `npm outdated`, direct OSV.dev API queries (pip-audit's venv bootstrap was failing locally on Python 3.14).

---

## Summary

| Priority | Count | Headline |
|---|---|---|
| **P0** | **2** | Critical/High Clerk SDK auth-bypass advisories (frontend + backend); High `urllib3` decompression-bomb redirect bypass + High `vite` arbitrary-file-read |
| P1 | 3 | Major-version-behind on `clerk-backend-api` (4 → 5); High advisories on `axios`, `react-router-dom`, `pyjwt`, `mako`, `cryptography` (all fixable patch/minor); pre-1.0 production deps (`sqlmodel 0.0.30`, `lucide-react 0.562`) |
| P2 | 4 | 3 unused declared deps (`pydantic-settings`, `zustand`, `@radix-ui/react-dialog`); inconsistent backend pinning (two separate dev groups); CI does not run dependency audit; bundle-size hotspots (`recharts` + `lightweight-charts` both shipped) |
| P3 | 1 | Minor outdated deps (`alembic`, `redis`, `uvicorn`, `pydantic`) one minor behind — straightforward upgrade |

**Total: 10 findings.**

**Total CVE / advisory counts obtained**:

- **npm**: 15 advisories — 1 critical, 9 high, 5 moderate, 0 low. All have fixes available.
- **PyPI** (via OSV.dev on the resolved lock — 51 packages queried): 9 advisories across 6 packages — 3 high, 5 moderate, 1 low. All have fixed versions published.

**Top concern**: Clerk SDK chain — `@clerk/shared` (transitive) carries a **critical** "middleware-based route protection bypass" plus `@clerk/clerk-react` and `@clerk/backend` carry **high** "authorization bypass when combining org/billing/reverification checks" advisories. Auth is the entire perimeter of this app — every API route sits behind these SDKs (per `CLAUDE.md`). With Phase B/C adding API-key auth and agent write access, anything Clerk-side that's currently advisory-flagged becomes a much larger blast radius.

---

## P0 — Blockers

### P0-1 — Critical/High Clerk SDK advisories (auth-bypass class)

**Source**: `npm audit` output saved to `/tmp/npm_audit.json`.

```
@clerk/shared        critical  Middleware-based route protection bypass
@clerk/clerk-react   high      Authorization bypass when combining org/billing/reverification checks
@clerk/backend       high      Authorization bypass when combining org/billing/reverification checks
```

`@clerk/clerk-react` is pinned at `^5.59.2` in `frontend/package.json`; `@clerk/backend` at `^2.29.0` in dev deps. `npm audit` reports `fixAvailable: true` for both — i.e., a non-breaking minor/patch upgrade resolves all three. `@clerk/shared` is transitive through both, so updating the two declared packages should pull the fix.

The Python equivalent — `clerk-backend-api 4.2.0` — is **two major versions behind** (latest: `5.0.6`). I did not find an OSV.dev advisory on the 4.x line, but the SDK is the JWT verification path for every authenticated endpoint, the 4→5 jump is large, and it should ride the same wave as the frontend bump (see P1-1).

**Fix**: in one PR — `npm install @clerk/clerk-react@latest @clerk/backend@latest` and bump `clerk-backend-api>=5.0.0` in `pyproject.toml`. Re-run `task ci`, then `npm audit` should return zero criticals.

---

### P0-2 — High advisories on `urllib3` and `vite`

**Source**: OSV.dev query (Python) and `npm audit` (npm).

Two unrelated high advisories that should land in the same patch wave:

- **`urllib3==2.6.2`** → `CVE-2026-21441` / `GHSA-38jv-5279-wg99` — **High**. "Decompression-bomb safeguards bypassed when following HTTP redirects (streaming API)." `urllib3` is transitive (via `requests` → Alpha Vantage adapters and `clerk-backend-api`'s HTTP path). Latest is `2.7.0`. Bump `urllib3>=2.7.0` constraint.
- **`vite ^6.0.7`** → 2 advisories — **High** "Arbitrary File Read via Vite Dev Server WebSocket" + Moderate path-traversal. Dev-only by definition (Vite is `devDependencies`), but this is also the local dev surface for every engineer — and the proposal calls for an OSS-ready posture (Q5). `npm audit` reports `fixAvailable: true`.

The dev-only nature of `vite` arguably makes it P1, but `urllib3` is shipped to production and the two pair cleanly into a single "patch the high-severity transient deps" PR, so I'm grouping them.

**Fix**: `npm install vite@latest`; for `urllib3`, the cleanest path is `uv lock --upgrade-package urllib3` (or a top-level constraint if the resolver doesn't pick up the latest).

---

## P1 — Important

### P1-1 — `clerk-backend-api` two major versions behind (4 → 5)

**File**: `backend/pyproject.toml:23` — `clerk-backend-api>=4.2.0`.

Latest is `5.0.6`. A 4→5 jump on the auth library that gates every API endpoint is exactly the upgrade you don't want to defer until Phase C, where the API-key path will be added on top of the Clerk verifier. Read the 5.x changelog before bumping; expect breaking changes around request/response models and async helpers.

This is paired with P0-1 because the frontend Clerk bump and the backend bump should land together (Clerk's session-token format is shared across SDK majors).

---

### P1-2 — Cluster of high/moderate Python advisories — all patchable

**Source**: OSV.dev query against the resolved lock.

| Package | Installed | Advisory | Severity | Notes |
|---|---|---|---|---|
| `pyjwt` | 2.10.1 | `CVE-2026-32597` (`GHSA-752w-5fwx-jx9f`) | High | "Accepts unknown `crit` header extensions". JWT verification is a hot path. Latest: `2.12.1`. |
| `cryptography` | 45.0.7 | `CVE-2026-26007` (`GHSA-r6ph-v2qm-q3c2`) + 2 more | High + Moderate + Low | Subgroup attack on SECT curves; buffer overflow on non-contiguous buffers; partial DNS name-constraint enforcement. Latest: `48.0.0`. |
| `mako` | 1.3.10 | `CVE-2026-44307` + `CVE-2026-41205` | High + Moderate | Path traversal in `TemplateLookup`. Transitive via `alembic`. Latest: `1.3.12`. |
| `requests` | 2.32.5 | `CVE-2026-25645` | Moderate | Insecure temp-file reuse in `extract_zipped_paths`. Latest: `2.33.1`. |
| `python-dotenv` | 1.2.1 | `CVE-2026-28684` | Moderate | Symlink-following in `set_key`. Latest: `1.2.2`. |

All five are minor/patch upgrades. Wrap them all into a single `uv lock --upgrade` PR and re-run `task ci`.

Frontend equivalent: `axios ^1.13.2` carries 3 advisories (NO_PROXY SSRF bypass; cloud-metadata exfiltration; auth-bypass via prototype pollution in `validateStatus`). Latest is `1.16.0` and the fix is non-breaking. Same PR or its own — but should not slip past Phase B.

---

### P1-3 — `react-router-dom` carrying high XSS / CSRF advisories

**File**: `frontend/package.json:38` — `react-router-dom: ^7.11.0`.

Three advisories on the transitive `react-router`: high XSS via open redirects, high SSR XSS in `ScrollRestoration`, moderate CSRF in action/server-action processing. We're on the SPA (client-rendered) router, so SSR XSS doesn't apply and the open-redirect XSS only bites if untrusted data hits a redirect target — but the proposal moves toward agent-driven flows where redirect targets may come from API state, raising the risk profile. `npm audit` reports `fixAvailable: true`.

---

### P1-4 — Pre-1.0 deps in production paths

| Package | Version | Where it sits |
|---|---|---|
| `sqlmodel` | `0.0.30` | Backend ORM — every domain entity goes through this (`from sqlmodel import …` in 22 files) |
| `lucide-react` | `^0.562.0` (latest `1.14.0` — first 1.x just released) | Icon library across UI |
| `class-variance-authority` | `^0.7.1` | Used in `cn()` utility — 4 callsites |

`sqlmodel 0.0.30` is the canonical pre-1.0-doing-critical-work case: 30 patch releases deep, no semver guarantees, and the upstream maintainer has been slow on releases. Migrating off (back to plain SQLAlchemy + Pydantic models, which is what `sqlmodel` thinly wraps) is a real chunk of work but should be **scoped now** before Phase C piles more strategy/agent entities onto the model layer. Latest `sqlmodel` is `0.0.38` — bump that in the meantime.

`lucide-react 1.x` just shipped; defer the major until 1.x stabilizes (P2 effectively). `class-variance-authority` is pinned by shadcn's setup; track but no action.

---

### P1-5 — One major-version-behind frontend dep: `lucide-react`

**File**: `frontend/package.json:34` — `lucide-react: ^0.562.0`. Latest stable is `1.14.0` (a true 0.x → 1.x jump). All other declared frontend deps are within `wanted` of `latest` per `npm outdated`. Tracking this one explicitly because everything else is actually current.

---

## P2 — Cleanups

### P2-1 — Three unused declared dependencies

Deps in `package.json` / `pyproject.toml` with **zero callsites** in `src/`:

- **`pydantic-settings>=2.6.0`** (`backend/pyproject.toml:14`). No `BaseSettings` / `SettingsConfigDict` / `pydantic_settings` import anywhere in `backend/src/` or `backend/tests/`. Config is loaded via raw `os.getenv` and TOML in `infrastructure/database.py` and elsewhere. Either drop the dep, or — better — adopt it (the proposal's Phase B will introduce more env vars and a typed settings module would help).
- **`zustand: ^5.0.3`** (`frontend/package.json:41`). Zero `from 'zustand'` imports in `frontend/src/`. State is held in TanStack Query + React component state. The convention listed in `CLAUDE.md` mentions Zustand explicitly, but it is currently unused — either drop it or adopt it consistently.
- **`@radix-ui/react-dialog: ^1.1.15`** (`frontend/package.json:25`). Zero imports in `frontend/src/`. `ConfirmDialog.tsx` and `Dialog.tsx` use the native `<dialog>` element instead. Drop or adopt.

Each is small in absolute size but worth resolving before Phase C: a stated convention that is silently ignored is a lurking source of inconsistency for new code (or for an agent generating UI).

### P2-2 — Inconsistent backend pinning + duplicate dev groups

`backend/pyproject.toml` declares dev dependencies in **two places**:

- `[project.optional-dependencies] dev` (lines 28–38) — pytest, pyright, ruff, etc.
- `[dependency-groups] dev` (lines 86–90) — playwright + requests

Pick one. uv supports both, but the duplication is confusing and `requests` in particular sits orphaned in the second group with no obvious purpose (no `requests` usage anywhere in the repo per grep — it's there for `pytest-recording`'s VCR cassettes? — flag for cleanup).

All deps are pinned with `>=` (loose). That's a defensible choice for a single-deployment project, but combined with the absence of CI-side `pip-audit` (P2-3) it means nothing alerts you when a transitive moves to a vulnerable version. Consider tightening to compatible-release (`~=`) on the load-bearing libs (`fastapi`, `pydantic`, `sqlmodel`, `clerk-backend-api`) and let `uv.lock` do the rest.

### P2-3 — CI runs no dependency audit

`.github/workflows/ci.yml` per the agent doc lists "security: dependency audit" but I see no `pip-audit` / `npm audit` step in this codebase (grep `pip-audit` and `npm audit` in `.github/workflows/` — no matches). With 15 npm advisories and 9 PyPI advisories sitting in `main`, a CI gate would already be screaming. Add:

```yaml
- run: cd frontend && npm audit --audit-level=high
- run: cd backend && uvx pip-audit -r <(uv pip freeze) --skip-editable
```

Set the threshold to `high` initially so we don't block on transient moderates.

### P2-4 — Bundle-size: two charting libs

Frontend ships **both** `recharts ^3.6.0` (used in `ComparisonChart.tsx`, `CompositionChart.tsx`, `CompositionOverTimeChart.tsx`, `PerformanceChart.tsx`) and `lightweight-charts ^5.1.0` (used in `LightweightPriceChart.tsx`). Recharts is ~150 KB minified+gzipped; Lightweight-Charts is ~50 KB. Together they're a noticeable share of the bundle and they overlap in capability (line/area charts). For Phase C's read-heavy agent dashboards, consolidate on one — likely `lightweight-charts` for trading-style charts, with custom SVG/recharts only where genuinely needed.

This is "track" not "fix"; flagging here so it's on the radar before more chart code lands.

---

## P3 — Defer

### P3-1 — Minor outdated deps (one-minor-behind cohort)

The cleanly-deferrable group: `alembic 1.17 → 1.18`, `redis 7.1 → 7.4`, `uvicorn 0.40 → 0.46`, `pydantic 2.12 → 2.13`, `pydantic-core 2.41 → 2.46`, `starlette 0.50 → 1.0`, `sqlalchemy 2.0.45 → 2.0.49`. Roll them up into a periodic "deps refresh" PR after the P0/P1 advisories are cleared. `starlette` going 0.50 → 1.0 sounds dramatic but it's the Starlette team finally cutting their first 1.0 — should be a non-breaking move.

---

## What was NOT a problem (confirming)

- **Licenses**: clean. 516 MIT, 39 ISC, 23 Apache-2.0, 10 BSD-2, 5 MPL-2.0, 5 BSD-3 — no GPL / AGPL / LGPL anywhere. One CC-BY-4.0 (`caniuse-lite`), which is data, not redistributed code. **OSS-readiness from a licensing angle is fine.**
- **Dev/prod separation**: clean. No test/lint/storybook/jsdom-class deps leaked into `dependencies`.
- **Date-lib duplication**: none. No `date-fns`, `dayjs`, `moment`, `luxon` declared or transitive at top level.
- **Heavy single-helper deps**: nothing egregious. Lucide-react is full-size but commonly tree-shaken; `@radix-ui/*` set is small; no `lodash` (only individual function imports if any).
- **Unused-but-declared async drivers**: `aiosqlite`, `asyncpg`, `greenlet` show zero direct imports. **These are correct** — they're driver strings (`sqlite+aiosqlite://`, `postgresql+asyncpg://`) and a SQLAlchemy async runtime requirement. Leave them.

---

## References

- `npm audit` output: `/tmp/npm_audit.json` (15 advisories — 1 critical / 9 high / 5 moderate)
- `uv pip list --outdated` output: 28 packages behind, captured during this audit
- OSV.dev API: queried against `uv pip freeze` output (51 packages); 9 advisories across 6 packages
- `pip-audit`: attempted via `uvx pip-audit` (project + requirements modes) — failed at venv bootstrap (`ensurepip` SIGABRT) on this macOS box; OSV.dev direct query used as substitute
