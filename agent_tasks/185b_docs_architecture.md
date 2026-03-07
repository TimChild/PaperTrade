# Docs Refactorer Task: Architecture Consolidation

**Target**: `docs/architecture/`

## Instructions

1.  **Analyze `docs/architecture/`**:
    - `phase4-refined/overview.md` (Seems to be the "latest").
    - `technical-boundaries.md` (Seems important).
    - `clerk-implementation-info.md` (Specific detail).

2.  **Consolidate**:
    - Promote `phase4-refined/overview.md` to `docs/architecture/README.md` (this becomes the source of truth).
    - Integrate `technical-boundaries.md` into the README or as a distinct "Technical Boundaries" section/linked file.
    - Check if `clerk-implementation-info.md` belongs in `docs/architecture` or closer to `authentication` docs. If strict Architecture, keep it or link it.

3.  **Cleanup**:
    - Delete `docs/architecture/phase4-refined/` folder after promoting its content.
    - Ensure `docs/architecture/README.md` is the entry point.
    - Archive old stuff if it conflicts, but `archived/` already exists.

4.  **Verification**:
    - Ensure the high-level architecture diagram/text is strictly visible at `docs/architecture/`.
