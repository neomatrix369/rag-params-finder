#!/bin/bash
set -e

# Usage: ./scripts/release.sh [major|minor|patch]
# Example: ./scripts/release.sh minor  # 0.11.0 → 0.12.0

RELEASE_TYPE=${1:-patch}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Get current version from pyproject.toml
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

# 2. Calculate next version
NEW_VERSION=$("$SCRIPT_DIR/bump_version.py" "$CURRENT_VERSION" "$RELEASE_TYPE")
echo "Next version: $NEW_VERSION"

# 3. Update version in files
echo "Updating version in files..."
sed -i.bak "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
sed -i.bak "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json

# Check if cli/main.py has VERSION constant
if grep -q "VERSION = " cli/main.py 2>/dev/null; then
    sed -i.bak "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" cli/main.py
fi

# Remove backup files
rm -f pyproject.toml.bak frontend/package.json.bak cli/main.py.bak 2>/dev/null || true

# 4. Prompt to update CHANGELOG.md
echo ""
echo "================================================"
echo "NEXT STEP: Update CHANGELOG.md"
echo "================================================"
echo ""
echo "Add the following section under ## [Unreleased]:"
echo ""
echo "## [$NEW_VERSION] - $(date +%Y-%m-%d)"
echo ""
echo "### Added"
echo "- "
echo ""
echo "### Changed"
echo "- "
echo ""
echo "### Fixed"
echo "- "
echo ""
echo "Press ENTER when you've updated CHANGELOG.md..."
read -r

# 5. Extract changelog for this version (between this version and next section)
CHANGELOG_EXCERPT=$(awk "/^## \[$NEW_VERSION\]/,/^## \[/" CHANGELOG.md | head -n -1)

if [ -z "$CHANGELOG_EXCERPT" ]; then
    echo "ERROR: Could not find [$NEW_VERSION] section in CHANGELOG.md"
    exit 1
fi

# 6. Commit version bump
git add pyproject.toml frontend/package.json CHANGELOG.md cli/main.py 2>/dev/null || true
git commit -m "chore: Bump version to $NEW_VERSION"

# 7. Create annotated tag
git tag -a "v$NEW_VERSION" -m "Release $NEW_VERSION

$CHANGELOG_EXCERPT"

echo ""
echo "✅ Created tag v$NEW_VERSION"

# 8. Ask before pushing
echo ""
echo "Ready to push commit and tag to origin?"
echo "  git push origin main"
echo "  git push origin v$NEW_VERSION"
read -p "Push now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin main
    git push origin "v$NEW_VERSION"
    echo "✅ Pushed to GitHub"

    # 9. Create GitHub release (if gh CLI installed)
    if command -v gh &> /dev/null; then
        read -p "Create GitHub release? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            gh release create "v$NEW_VERSION" \
                --title "v$NEW_VERSION" \
                --notes "$CHANGELOG_EXCERPT"
            echo "✅ GitHub release created"
        fi
    else
        echo "💡 Install gh CLI to auto-create GitHub releases: brew install gh"
    fi
else
    echo "Skipped push. Run manually:"
    echo "  git push origin main && git push origin v$NEW_VERSION"
fi
