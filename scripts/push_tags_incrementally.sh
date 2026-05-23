#!/bin/bash
# Push tags and create GitHub releases one at a time
# This builds up the release history incrementally

set -e

# Tag list in chronological order
TAGS=(
    "v0.0.1:2026-04-15:Initial Architecture"
    "v0.1.0:2026-05-02:Slice 1 - Skateboard"
    "v0.2.0:2026-05-02:Slices 2-5 - Core Features"
    "v0.3.0:2026-05-02:Slice 7 - Local Models"
    "v0.4.0:2026-05-17:Slice 6 - Chunkers + Retrieval"
    "v0.4.1:2026-05-05:Docs + CI Polish"
    "v0.5.0:2026-05-17:Slice 8 - Dashboard UX"
    "v0.6.0:2026-05-19:Slice 9 - Deletion"
    "v0.7.0:2026-05-19:Vector DB Stats + Pause/Resume"
    "v0.7.1:2026-05-19:Dashboard Polling"
    "v0.8.0:2026-05-20:Kimchi Provider"
    "v0.8.1:2026-05-20:Provider Tests"
    "v0.9.0:2026-05-23:Search Index Preflight"
    "v0.9.1:2026-05-23:Scoped Logging + Voyage UX"
    "v0.10.0:2026-05-23:Slice 18 - Unified Retriever"
    "v0.11.0:2026-05-23:Weighted Averaging"
)

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: gh CLI is not installed"
    echo "Install with: brew install gh  (macOS)"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "=================================================="
echo "Incremental Tag Push & Release Creation"
echo "=================================================="
echo ""
echo "This will push 15 tags and create GitHub releases"
echo "one at a time in chronological order."
echo ""
read -p "Ready to start? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

COUNT=0
TOTAL=${#TAGS[@]}

for TAG_INFO in "${TAGS[@]}"; do
    IFS=':' read -r TAG DATE TITLE <<< "$TAG_INFO"
    COUNT=$((COUNT + 1))

    echo ""
    echo "=================================================="
    echo "[$COUNT/$TOTAL] Processing $TAG"
    echo "=================================================="
    echo "Date:  $DATE"
    echo "Title: $TITLE"
    echo ""

    # Extract tag message
    NOTES=$(git tag -l --format='%(contents)' "$TAG")

    if [ -z "$NOTES" ]; then
        echo "⚠️  Warning: No tag message found for $TAG"
        continue
    fi

    # Show tag message preview
    echo "Tag message preview:"
    echo "---"
    echo "$NOTES" | head -10
    echo "---"
    echo ""

    # Push the tag
    echo "Step 1: Pushing tag to GitHub..."
    if git push origin "$TAG" 2>/dev/null; then
        echo "✅ Tag $TAG pushed to GitHub"
    else
        echo "⚠️  Tag $TAG already exists on GitHub (skipping push)"
    fi

    # Create GitHub release
    echo ""
    echo "Step 2: Creating GitHub release..."
    if gh release create "$TAG" \
        --title "$TITLE" \
        --notes "$NOTES" 2>/dev/null; then
        echo "✅ GitHub release created for $TAG"
    else
        echo "⚠️  Release $TAG already exists on GitHub (skipping)"
    fi

    echo ""
    echo "✅ Completed $TAG"

    # Pause between releases (except for the last one)
    if [ $COUNT -lt $TOTAL ]; then
        echo ""
        read -p "Continue to next release? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            echo "Paused at $TAG ($COUNT/$TOTAL completed)"
            echo "Run this script again to continue from where you left off."
            exit 0
        fi
    fi
done

echo ""
echo "=================================================="
echo "🎉 All Done!"
echo "=================================================="
echo ""
echo "Created $TOTAL GitHub releases in chronological order."
echo ""
echo "View releases at:"
echo "https://github.com/neomatrix369/rag-params-finder/releases"
echo ""
echo "View tags:"
git tag -l | sort -V
