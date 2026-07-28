#!/bin/bash
set -e
set -o pipefail

# Usage: ./scripts/release/release.sh [major|minor|patch]
# Example: ./scripts/release/release.sh minor  # 0.12.0 → 0.13.0
#
# Releases go through a branch + PR — never push the version bump directly to main.

RELEASE_TYPE=${1:-patch}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

# 0. Preflight — must start from a clean main (or ask)
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: Start on main before releasing (current: $CURRENT_BRANCH)."
  echo "  git checkout main && git pull origin main"
  exit 1
fi

if [[ -n "$(git status --short)" ]]; then
  echo "ERROR: Working tree is dirty. Commit or stash before releasing."
  git status --short
  exit 1
fi

# 1. Get current version from pyproject.toml
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

# 2. Calculate next version
NEW_VERSION=$("$SCRIPT_DIR/bump_version.py" "$CURRENT_VERSION" "$RELEASE_TYPE")
echo "Next version: $NEW_VERSION"
RELEASE_BRANCH="release/v${NEW_VERSION}"

if git show-ref --verify --quiet "refs/heads/${RELEASE_BRANCH}" \
  || git show-ref --verify --quiet "refs/remotes/origin/${RELEASE_BRANCH}"; then
  echo "ERROR: Branch ${RELEASE_BRANCH} already exists. Aborting."
  exit 1
fi

if git tag -l "v${NEW_VERSION}" | grep -q .; then
  echo "ERROR: Tag v${NEW_VERSION} already exists. Aborting."
  exit 1
fi

# 3. Create release branch (never bump on main)
echo "Creating branch ${RELEASE_BRANCH}..."
git checkout -b "$RELEASE_BRANCH"

# 4. Update version in files
echo "Updating version in files..."
sed -i.bak "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
sed -i.bak "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json

# Check if cli/main.py has VERSION constant
if grep -q "VERSION = " cli/main.py 2>/dev/null; then
  sed -i.bak "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" cli/main.py
fi

# Remove backup files
rm -f pyproject.toml.bak frontend/package.json.bak cli/main.py.bak 2>/dev/null || true

# 5. Prompt to update CHANGELOG.md
echo ""
echo "================================================"
echo "NEXT STEP: Update CHANGELOG.md"
echo "================================================"
echo ""
echo "Promote ## [Unreleased] body to:"
echo ""
echo "## [$NEW_VERSION] - $(date +%Y-%m-%d)"
echo ""
echo "Leave a fresh empty ## [Unreleased] section above it."
echo ""
echo "Also update docs/plan/slices/PROGRESS.md Release Cadence"
echo "  Current version → v$NEW_VERSION"
echo ""
echo "Press ENTER when you've updated CHANGELOG.md (and PROGRESS if desired)..."
read -r

# 6. Extract changelog for this version (macOS-safe; no head -n -1)
CHANGELOG_EXCERPT=$(awk "/^## \\[$NEW_VERSION\\]/{p=1} p{if(/^## \\[/ && !/^## \\[$NEW_VERSION\\]/){exit} print}" CHANGELOG.md)

if [[ -z "$CHANGELOG_EXCERPT" ]]; then
  echo "ERROR: Could not find [$NEW_VERSION] section in CHANGELOG.md"
  echo "Restoring files and returning to main..."
  git checkout -- pyproject.toml frontend/package.json cli/main.py CHANGELOG.md 2>/dev/null || true
  git checkout main
  git branch -D "$RELEASE_BRANCH"
  exit 1
fi

# 7. Commit version bump on the release branch
git add pyproject.toml frontend/package.json CHANGELOG.md cli/main.py docs/plan/slices/PROGRESS.md 2>/dev/null || true
git status --short
git commit -m "chore: Bump version to $NEW_VERSION"

echo ""
echo "✅ Committed on ${RELEASE_BRANCH}"
echo "   Tag + GitHub release happen AFTER the PR merges to main."

# 8. Ask before pushing the branch (never main)
echo ""
echo "Ready to push release branch and open a PR?"
echo "  git push -u origin ${RELEASE_BRANCH}"
echo "  gh pr create → main"
read -p "Push branch + open PR? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  git push -u origin "$RELEASE_BRANCH"
  echo "✅ Pushed ${RELEASE_BRANCH}"

  if command -v gh &>/dev/null; then
    PR_URL=$(gh pr create \
      --base main \
      --head "$RELEASE_BRANCH" \
      --title "chore(release): bump to v${NEW_VERSION}" \
      --body "$(cat <<EOF
## Summary
- Bump version **${CURRENT_VERSION} → ${NEW_VERSION}** (\`${RELEASE_TYPE}\`)
- Promote CHANGELOG \`[Unreleased]\` → \`[${NEW_VERSION}]\`

## After merge
\`\`\`bash
git checkout main && git pull origin main
git tag -a "v${NEW_VERSION}" -m "Release ${NEW_VERSION}"
git push origin "v${NEW_VERSION}"
gh release create "v${NEW_VERSION}" --title "v${NEW_VERSION}" --notes-file - <<'NOTES'
${CHANGELOG_EXCERPT}
NOTES
\`\`\`

## Test plan
- [ ] CI green on this PR
- [ ] CHANGELOG has \`[${NEW_VERSION}]\` section
- [ ] \`pyproject.toml\` / \`frontend/package.json\` show ${NEW_VERSION}
EOF
)")
    echo "✅ PR opened: ${PR_URL}"
  else
    echo "💡 Install gh CLI to open the PR automatically: brew install gh"
    echo "   Or open: https://github.com/neomatrix369/rag-params-finder/compare/main...${RELEASE_BRANCH}"
  fi
else
  echo "Skipped push. When ready:"
  echo "  git push -u origin ${RELEASE_BRANCH}"
  echo "  gh pr create --base main --head ${RELEASE_BRANCH}"
fi

echo ""
echo "================================================"
echo "Do NOT push this bump to main directly."
echo "Merge the PR, then tag + gh release on main."
echo "================================================"
