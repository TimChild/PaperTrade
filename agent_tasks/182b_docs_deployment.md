# Docs Consolidation: Deployment

**Objective**: Create a definitive "Deployment Guide" and archive out-of-date experiments.

## Input Files
- `docs/deployment/community-scripts-reference.md`
- `docs/deployment/domain-and-ssl-setup.md`
- `docs/deployment/production-checklist.md`
- `docs/deployment/proxmox-environment-reference.md`
- `docs/deployment/proxmox-learnings.md`
- `docs/deployment/proxmox-vm-approach-comparison.md`
- `docs/deployment/proxmox-vm-deployment.md`
- `scripts/proxmox-vm/`

## Goals
1. **Clarify Production vs Local**: Separate the "how to deploy to Prod/Proxmox" from "how to run local Docker".
2. **Consolidate Proxmox Info**: We have a lot of "learnings" and "comparisons" and "deployment guides". Merge into a single `docs/deployment/proxmox-guide.md` (or similar).
3. **Archive**: Move historical comparisons or "learnings" that are no longer actionable to an archive section or just delete them if the info is integrated.

## Desired Output Structure (Suggestion)
- `docs/deployment/README.md` (Index)
- `docs/deployment/proxmox.md` (The definitive Proxmox guide)
- `docs/deployment/domain-setup.md` (Domain & SSL)
- `docs/deployment/production-checklist.md` (Keep this, it's useful context)
- (Archive/Delete the rest)

## Instructions
- Read all inputs.
- Identify the most recent, working instructions for Proxmox deployment.
- Create new consolidated file(s).
- Update links.
- Delete old files.
