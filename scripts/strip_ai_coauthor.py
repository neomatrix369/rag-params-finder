#!/usr/bin/env python3
"""commit-msg hook: remove AI co-author trailers injected by Cursor / Claude.

Strips any trailer line matching:
  Co-authored-by: Cursor <cursoragent@cursor.com>
  Co-authored-by: Claude <...@anthropic.com>
  Co-authored-by: <anything containing Cursor|Claude|Anthropic>

Usage (called by pre-commit at commit-msg stage):
    python scripts/strip_ai_coauthor.py <path-to-COMMIT_EDITMSG>
"""

from __future__ import annotations

import re
import sys

_STRIP = re.compile(
    r"^Co-authored-by:.*(?:Cursor|cursoragent|Claude|Anthropic)",
    re.IGNORECASE,
)


def strip_ai_trailers(msg_file: str) -> None:
    with open(msg_file, encoding="utf-8") as handle:
        lines = handle.readlines()

    cleaned = [line for line in lines if not _STRIP.match(line)]

    while cleaned and cleaned[-1].strip() == "":
        cleaned.pop()
    if cleaned:
        cleaned.append("\n")

    with open(msg_file, "w", encoding="utf-8") as handle:
        handle.writelines(cleaned)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <commit-msg-file>")
    strip_ai_trailers(sys.argv[1])
