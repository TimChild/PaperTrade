#!/usr/bin/env python3
"""Fix common Markdown rendering issues that affect MkDocs / CommonMark output.

Currently fixes two patterns:

1. **Missing blank lines around lists/tables.** CommonMark won't recognize a
   list or table that starts immediately after a paragraph or ends without
   a blank line before the next paragraph; the block renders as run-on text.
   We insert blank lines before the first and after the last item of each
   such block.

2. **Adjacent bold-label metadata lines collapsing into one paragraph.**
   When you write a block like:

       **Status**: Draft
       **Author**: Tim
       **Created**: 2026-05-10

   CommonMark treats the line breaks as soft wraps and renders the block as
   one paragraph. The fix is to append two trailing spaces (the explicit
   hard-break marker) to all but the last line. We auto-detect runs of two
   or more adjacent ``**Label**:`` lines and apply the fix.

   IMPORTANT: the project's pre-commit ``trailing-whitespace`` hook is
   configured with ``--markdown-linebreak-ext=md,markdown`` so these
   intentional two-space breaks are preserved — see
   ``.pre-commit-config.yaml``. If the hook ever loses that flag, this
   fix will be silently undone on push.

Code blocks (fenced with ``` or ~~~) are preserved verbatim. The script is
idempotent — running it twice produces the same output as running it once.

Usage:
    uv run scripts/fix_md_rendering.py PATH [PATH ...]
    # PATH can be a file or directory; directories are walked recursively.

    uv run scripts/fix_md_rendering.py docs/              # rewrite in place
    uv run scripts/fix_md_rendering.py --check docs/      # exit 1 if changes needed
    uv run scripts/fix_md_rendering.py --diff docs/       # show diffs without writing

Limitations:
- Multi-line list items (continuation lines indented under a list marker) are
  not specially detected. If you have such items they're still preserved, but
  if a continuation line has no list marker and is followed by a non-list
  paragraph, a blank line will get inserted between them. In practice this is
  rare in our docs.
- The metadata-block hard-break fix only triggers on bold-label syntax
  (``**Label**: value``). Other metadata-shaped patterns (plain ``Label:``)
  are left alone to avoid false positives in prose.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
META_RE = re.compile(r"^\s*\*\*[^*]+\*\*:")


def classify(lines: list[str]) -> tuple[list[bool], list[bool]]:
    """Return (is_list_line, is_table_line) per input line, ignoring code-fence content."""
    in_fence = False
    is_list: list[bool] = []
    is_table: list[bool] = []
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            is_list.append(False)
            is_table.append(False)
            continue
        if in_fence:
            is_list.append(False)
            is_table.append(False)
            continue
        is_list.append(bool(LIST_RE.match(line)))
        is_table.append(bool(TABLE_RE.match(line)))
    return is_list, is_table


def fix_block_blank_lines(lines: list[str]) -> list[str]:
    """Insert blank lines before/after every list or table block."""
    is_list, is_table = classify(lines)
    is_block = [a or b for a, b in zip(is_list, is_table)]

    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if not is_block[i]:
            out.append(lines[i])
            i += 1
            continue

        if out and out[-1].strip() != "":
            out.append("")

        k = i
        while k < n:
            if is_block[k]:
                k += 1
                continue
            if lines[k].strip() == "" and k + 1 < n and is_block[k + 1]:
                k += 1
                continue
            break

        out.extend(lines[i:k])

        if k < n and lines[k].strip() != "":
            out.append("")
        i = k
    return out


def fix_metadata_hard_breaks(lines: list[str]) -> list[str]:
    """Append two-space hard breaks to all-but-last line of bold-label metadata runs.

    A "run" is two or more consecutive lines all matching ``**Label**:`` shape
    (outside of fenced code blocks). The trailing two spaces force a ``<br>``
    in CommonMark output without breaking the paragraph.
    """
    in_fence = False
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        if META_RE.match(line):
            j = i
            while j < n and META_RE.match(lines[j]):
                j += 1
            run_len = j - i
            if run_len >= 2:
                for k in range(i, j - 1):
                    # Idempotent: strip any existing trailing whitespace, then add exactly "  ".
                    out.append(lines[k].rstrip() + "  ")
                out.append(lines[j - 1])
            else:
                out.append(line)
            i = j
            continue
        out.append(line)
        i += 1
    return out


def fix(text: str) -> str:
    """Apply all fixers in order."""
    if not text:
        return text
    had_trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    if had_trailing_nl:
        lines.pop()

    lines = fix_block_blank_lines(lines)
    lines = fix_metadata_hard_breaks(lines)

    result = "\n".join(lines)
    if had_trailing_nl:
        result += "\n"
    return result


def iter_md_paths(targets: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for t in targets:
        if t.is_file() and t.suffix.lower() in {".md", ".markdown"}:
            paths.append(t)
        elif t.is_dir():
            paths.extend(p for p in t.rglob("*.md"))
            paths.extend(p for p in t.rglob("*.markdown"))
        else:
            print(f"warning: {t} is not a Markdown file or directory", file=sys.stderr)
    return sorted(set(paths))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown file(s) or directory(ies)")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any file would change; do not write")
    parser.add_argument("--diff", action="store_true", help="Print unified diff of changes; do not write")
    args = parser.parse_args(argv)

    files = iter_md_paths(args.paths)
    if not files:
        print("no markdown files found", file=sys.stderr)
        return 1

    changed = 0
    for fp in files:
        original = fp.read_text(encoding="utf-8")
        fixed = fix(original)
        if fixed == original:
            continue
        changed += 1
        if args.diff:
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile=str(fp),
                tofile=str(fp) + " (fixed)",
            )
            sys.stdout.writelines(diff)
        elif args.check:
            print(f"would fix: {fp}")
        else:
            fp.write_text(fixed, encoding="utf-8")
            print(f"fixed: {fp}")

    if args.check and changed:
        return 1
    if changed == 0:
        print("no changes needed")
    else:
        print(f"{'would fix' if args.check else 'fixed'}: {changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
