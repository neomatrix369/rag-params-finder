#!/bin/bash
# Create all retrospective GitHub releases
# Requires: gh CLI authenticated (gh auth login)

set -e

TAGS=(
    "v0.0.1:Initial Architecture"
    "v0.1.0:Slice 1 - Skateboard"
    "v0.2.0:Slices 2-5 - Core Features"
    "v0.3.0:Slice 7 - Local Models"
    "v0.4.0:Slice 6 - Chunkers + Retrieval"
    "v0.4.1:Docs + CI Polish"
    "v0.5.0:Slice 8 - Dashboard UX"
    "v0.6.0:Slice 9 - Deletion"
    "v0.7.0:Vector DB Stats + Pause/Resume"
    "v0.7.1:Dashboard Polling"
    "v0.8.0:Kimchi Provider"
    "v0.8.1:Provider Tests"
    "v0.9.0:Search Index Preflight"
    "v0.9.1:Scoped Logging"
    "v0.10.0:Slice 18 - Unified Retriever"
    "v0.11.0:Weighted Averaging"
)

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: gh CLI is not installed"
    echo "Install with: brew install gh  (macOS)"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "Creating 15 retrospective GitHub releases..."
echo ""

for TAG_INFO in "${TAGS[@]}"; do
    IFS=':' read -r TAG TITLE <<< "$TAG_INFO"

    echo "Creating release for $TAG: $TITLE"

    # Extract tag message as release notes
    NOTES=$(git tag -l --format='%(contents)' "$TAG")

    if [ -z "$NOTES" ]; then
        echo "  ⚠ Warning: No tag message found for $TAG, skipping..."
        continue
    fi

    # Create release
    if gh release create "$TAG" \
        --title "$TITLE" \
        --notes "$NOTES" 2>/dev/null; then
        echo "  ✅ $TAG released"
    else
        echo "  ⚠ $TAG already exists or failed to create"
    fi

    echo ""
done

echo "Done! Created releases for all tags."
echo "View at: https://github.com/neomatrix369/rag-params-finder/releases"
