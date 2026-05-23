#!/usr/bin/env python3
"""
Semantic version bumper for rag-params-finder.

Usage:
    ./bump_version.py 0.11.0 minor  # → 0.12.0
    ./bump_version.py 0.11.0 patch  # → 0.11.1
    ./bump_version.py 0.11.0 major  # → 1.0.0
"""

import sys


def bump_version(current: str, part: str) -> str:
    """Bump semantic version: major.minor.patch"""
    try:
        major, minor, patch = map(int, current.split("."))
    except ValueError:
        raise ValueError(f"Invalid version format: {current} (expected X.Y.Z)")

    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid part: {part} (expected major, minor, or patch)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: bump_version.py <current_version> <major|minor|patch>")
        sys.exit(1)

    current_version = sys.argv[1]
    bump_type = sys.argv[2]

    try:
        new_version = bump_version(current_version, bump_type)
        print(new_version)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
