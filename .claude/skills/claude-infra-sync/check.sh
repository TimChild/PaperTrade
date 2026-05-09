#!/usr/bin/env bash
# .claude/skills/claude-infra-sync/check.sh
#
# Bundled helper for the claude-infra-sync skill. Runs the simple grep-based
# subset of the lint passes and prints raw signals to stdout. The agent
# invoking the skill is expected to read this output, apply judgment, and
# write the formal report at agent_docs/sync-checks/YYYY-MM-DD/REPORT.md.
#
# This script does NOT write the report itself — keeping the procedural
# logic in the SKILL.md prose so it stays editable as a knowledge artifact.
#
# Usage: from the repo root,
#   bash .claude/skills/claude-infra-sync/check.sh
#
# Exit code is always 0 — findings are signal, not failure. The skill calibrates.

set -u

# Find the repo root (the one with CLAUDE.md at the top), so the script works
# from a worktree or a subdirectory.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

if [ ! -f CLAUDE.md ]; then
  echo "ERROR: no CLAUDE.md at repo root ($REPO_ROOT). Aborting." >&2
  exit 1
fi

echo "=========================================="
echo "claude-infra-sync — raw signals"
echo "Repo: $REPO_ROOT"
echo "Date: $(date +%Y-%m-%d)"
echo "=========================================="
echo

# --- Snapshot ----------------------------------------------------------------
echo "## Snapshot"
echo
echo "Agents:"
ls .claude/agents/ 2>/dev/null | sed 's/^/  /'
echo
echo "Skills:"
ls .claude/skills/ 2>/dev/null | sed 's/^/  /'
echo
echo "Claude infra line counts:"
wc -l CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md 2>/dev/null | tail -1
echo
echo "Most recent task number:"
ls agent_docs/tasks/ 2>/dev/null | grep -E '^[0-9]' | sort -n | tail -1 | sed 's/^/  /'
echo

# --- Pass 1 — Stale paths ----------------------------------------------------
echo "## Pass 1 — Stale paths (file references)"
echo
# Extract candidate paths from agent / skill / CLAUDE.md files.
candidates=$(grep -hoE '`[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.(md|py|ts|tsx|toml|json|yaml|yml)`' \
  CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md 2>/dev/null \
  | tr -d '`' | sort -u)

missing=0
while IFS= read -r path; do
  [ -z "$path" ] && continue
  # Skip placeholders (NNN_, YYYY-, wildcards, dated example filenames)
  case "$path" in
    *NNN_*|*\**|*YYYY-*) continue ;;
  esac
  if [ ! -e "$path" ]; then
    echo "  MISSING: $path"
    missing=$((missing + 1))
  fi
done <<< "$candidates"
echo
echo "  (total missing: $missing)"
echo "  Note: triage by hand — some matches will be example/template paths"
echo "        (relative shortpaths, code-block examples) that should be filtered."
echo

# Directory-shaped references
echo "## Pass 1b — Stale paths (directory references)"
echo
dir_candidates=$(grep -hoE '`[A-Za-z0-9_./-]+/`' \
  CLAUDE.md .claude/agents/*.md .claude/skills/*/SKILL.md 2>/dev/null \
  | tr -d '`' | sort -u)

missing_dirs=0
while IFS= read -r d; do
  [ -z "$d" ] && continue
  case "$d" in
    *NNN_*|*\**) continue ;;
  esac
  if [ ! -d "$d" ]; then
    echo "  MISSING DIR: $d"
    missing_dirs=$((missing_dirs + 1))
  fi
done <<< "$dir_candidates"
echo
echo "  (total missing dirs: $missing_dirs)"
echo

# --- Pass 3 — Skills inventory drift ----------------------------------------
echo "## Pass 3 — Skills inventory (CLAUDE.md vs filesystem)"
echo
# Pull only table rows (lines starting with `|`) inside the skills section
claude_skills=$(awk '/^## Project skills/{flag=1; next} /^## /{flag=0} flag' CLAUDE.md 2>/dev/null \
  | grep '^|' | grep -oE '`[a-z0-9-]+`' | tr -d '`' | sort -u)
disk_skills=$(ls .claude/skills/ 2>/dev/null | sort -u)

echo "In CLAUDE.md but missing on disk:"
echo "$claude_skills" | while IFS= read -r s; do
  [ -z "$s" ] && continue
  if [ ! -d ".claude/skills/$s" ]; then
    echo "  MISSING: $s"
  fi
done
echo
echo "On disk but missing from CLAUDE.md:"
echo "$disk_skills" | while IFS= read -r s; do
  [ -z "$s" ] && continue
  if ! echo "$claude_skills" | grep -qx "$s"; then
    echo "  ORPHAN: $s"
  fi
done
echo

# --- Pass 4 — Agents inventory drift ----------------------------------------
echo "## Pass 4 — Agents inventory (CLAUDE.md vs filesystem)"
echo
claude_agents=$(awk '/^## Specialist agents/{flag=1; next} /^## /{flag=0} flag' CLAUDE.md 2>/dev/null \
  | grep '^|' | grep -oE '`[a-z0-9-]+`' | tr -d '`' | sort -u)
disk_agents=$(ls .claude/agents/ 2>/dev/null | sed 's/\.md$//' | sort -u)

echo "In CLAUDE.md but missing on disk:"
echo "$claude_agents" | while IFS= read -r a; do
  [ -z "$a" ] && continue
  if [ ! -f ".claude/agents/$a.md" ]; then
    echo "  MISSING: $a"
  fi
done
echo
echo "On disk but missing from CLAUDE.md:"
echo "$disk_agents" | while IFS= read -r a; do
  [ -z "$a" ] && continue
  if ! echo "$claude_agents" | grep -qx "$a"; then
    echo "  ORPHAN: $a"
  fi
done
echo

# --- Pass 5 — Test count claims ----------------------------------------------
echo "## Pass 5 — Test count claims"
echo
grep -rEn '\b[0-9]{3,4}\s*tests?\b' \
  CLAUDE.md README.md PROGRESS.md .claude/ docs/ 2>/dev/null \
  | head -20 | sed 's/^/  /'
echo

# --- Pass 6 — Framework version claims ---------------------------------------
echo "## Pass 6 — Framework version claims"
echo
echo "Claims in agent / Claude files:"
grep -rEn 'React [0-9]+\+?|Python [0-9]\.?[0-9]*\+?|Node [0-9]+|TypeScript [0-9]+\.[0-9]+' \
  CLAUDE.md .claude/ 2>/dev/null | sed 's/^/  /'
echo
echo "Sources of truth:"
[ -f frontend/package.json ] && {
  echo "  frontend/package.json:"
  grep -E '"react"|"@types/react"|"typescript"|"vite"' frontend/package.json | sed 's/^/    /'
}
[ -f backend/pyproject.toml ] && {
  echo "  backend/pyproject.toml:"
  grep -E '^requires-python|^python =' backend/pyproject.toml | sed 's/^/    /'
}
echo

# --- Pass 7 — Endpoint references --------------------------------------------
echo "## Pass 7 — API endpoint references in agent files"
echo
endpoints=$(grep -rhoE '/api/v[0-9]+/[A-Za-z0-9_/-]+' .claude/agents/ CLAUDE.md 2>/dev/null | sort -u)
if [ -z "$endpoints" ]; then
  echo "  (none — skip)"
else
  echo "$endpoints" | sed 's/^/  /'
  echo
  echo "Cross-check against router declarations:"
  grep -rEn '@router\.(get|post|put|patch|delete)' \
    backend/src/zebu/adapters/inbound/api/ 2>/dev/null | head -20 | sed 's/^/  /'
fi
echo

# --- Pass 9 — Terminology drift ----------------------------------------------
echo "## Pass 9 — Terminology drift (specialist agent / subagent / etc.)"
echo
for term in "specialist agent" "subagent" "sub-agent" "specialist-agent"; do
  count=$(grep -rE "$term" CLAUDE.md .claude/ 2>/dev/null | wc -l | tr -d ' ')
  echo "  '$term': $count occurrences"
done
echo

# --- Pass 10 — Single-source-of-truth ----------------------------------------
echo "## Pass 10 — 'next task number' / single-source-of-truth signals"
echo
grep -rEn 'next (number|task)( is)?( the)? (\*\*)?[0-9]+' \
  CLAUDE.md agent_docs/README.md .claude/ 2>/dev/null | sed 's/^/  /'
echo

echo "=========================================="
echo "Done. Review signals above and write the formal report at"
echo "  agent_docs/sync-checks/$(date +%Y-%m-%d)/REPORT.md"
echo "following the skeleton in .claude/skills/claude-infra-sync/SKILL.md."
echo "=========================================="
