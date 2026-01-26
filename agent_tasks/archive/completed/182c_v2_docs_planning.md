# Docs Consolidation: Planning & Roadmap

**Objective**: Clean up the planning directory to have a single source of truth for the roadmap.

## Input Files
- `docs/planning/executive-summary.md`
- `docs/planning/product-roadmap.md`
- `docs/planning/feature-status.md`
- `docs/planning/project_plan.md`
- `docs/planning/project_strategy.md`
- `docs/planning/future-ideas.md`
- `docs/planning/ux-polish-phase-plan.md`
- `docs/planning/strategic-plan-2026-01-14.md`

## Goals
1. **Single Roadmap**: `product-roadmap.md`, `project_plan.md`, `feature-status.md` often overlap. Decide on ONE main "Roadmap" document (probably `product-roadmap.md`) and one "Implementation Plan" (current phase).
2. **Archive Old Plans**: `strategic-plan-2026-01-14.md`, `ux-polish-phase-plan.md` (if completed) should be archived.
3. **Executive Summary**: Ensure `executive-summary.md` is actually current (it claims "Phase 2 Complete" in some places, but we are past that).

## Desired Output Structure (Suggestion)
- `docs/planning/roadmap.md` (High level vision & timeline - rename `product-roadmap.md`)
- `docs/planning/features.md` (The feature matrix)
- `docs/planning/architecture-strategy.md` (Rename `project_strategy.md` if it covers tech strategy)
- `docs/planning/archive/` (Move dated plans here)

## Instructions
- Review all files.
- Update `roadmap.md` to reflect current status (Phase 3c/Polish complete).
- Move completed phase plans to archive.
- Ensure `future-ideas.md` is still relevant or merge into roadmap.
