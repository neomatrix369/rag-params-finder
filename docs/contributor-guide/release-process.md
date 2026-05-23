# Release Process

## Overview

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (x.0.0) — Breaking changes (rare)
- **MINOR** (0.x.0) — New features, completed slices (backward compatible)
- **PATCH** (0.0.x) — Bug fixes, polish, documentation improvements

**Typical cadence:**
- Major slice completion → **minor** bump (e.g., Slice 19 → v0.12.0)
- Enhancement/polish → **patch** bump (e.g., logging improvement → v0.12.1)

---

## Creating a Release

### 1. Complete the work

- Finish slice implementation
- All tests pass (`uv run pytest`, `npm run typecheck`)
- Update `docs/_internal/PROGRESS.md` to mark slice complete
- Commit work with clear messages

### 2. Update CHANGELOG.md

Add new section under `## [Unreleased]`:

```markdown
## [0.12.0] - YYYY-MM-DD

### Added
- Feature description (what it does, why it matters)

### Changed
- What behavior changed

### Fixed
- What bugs were fixed
```

Move appropriate items from `## [Unreleased]` to the new version.

### 3. Run the release script

```bash
# For a new slice (feature)
./scripts/release.sh minor

# For polish/enhancement
./scripts/release.sh patch

# For breaking change (rare)
./scripts/release.sh major
```

The script will:
1. Calculate next version
2. Update `pyproject.toml`, `frontend/package.json`
3. Prompt you to verify CHANGELOG.md
4. Create commit: "chore: Bump version to X.Y.Z"
5. Create annotated git tag with CHANGELOG excerpt
6. Ask permission to push
7. Optionally create GitHub release (if `gh` CLI installed)

### 4. Verify the release

Check:
- GitHub releases: `https://github.com/neomatrix369/rag-params-finder/releases`
- Git tags: `git tag -l`
- CLI version: `rag-params-finder version` (should show new version)

---

## Hotfix Process

For urgent fixes to a released version:

1. Create branch from release tag:
   ```bash
   git checkout -b hotfix/0.11.1 v0.11.0
   ```

2. Apply the fix and commit

3. Run release script:
   ```bash
   ./scripts/release.sh patch
   ```

4. Merge back to main:
   ```bash
   git checkout main
   git merge hotfix/0.11.1
   git push origin main
   ```

---

## Slice-to-Version Mapping Guide

| Slice Type | Version Bump | Example |
|------------|--------------|---------|
| Numbered slice (1-9, 10+) | Minor | Slice 19 → v0.12.0 |
| Major feature (pause/resume, deletion) | Minor | v0.7.0 |
| New provider support | Minor | Kimchi → v0.8.0 |
| Dashboard UX overhaul | Minor | Slice 8 → v0.5.0 |
| Docs polish, CI setup | Patch | ADRs → v0.4.1 |
| Logging improvements | Patch | Scoped logging → v0.9.1 |
| Performance optimization | Patch | Thread pools → v0.7.1 |
| Bug fix | Patch | Fix rerank score → v0.X.1 |

---

## CHANGELOG.md Guidelines

Follow [Keep a Changelog](https://keepachangelog.com/) format:

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

Each entry should:
- Start with a verb ("Add", "Fix", "Update", "Remove")
- Explain WHAT changed and WHY it matters (user perspective)
- Link to relevant slice specs or ADRs if helpful

**Good:**
> - Add weighted averaging metric (query_avg_score) for query-level fairness
> - Fix rerank score normalization to handle negative values

**Bad:**
> - Added new feature
> - Bug fix

---

## Version Bump Decision Tree

```
Is this a breaking change?
├─ Yes → MAJOR (x.0.0)
└─ No
   ├─ New feature or slice complete?
   │  └─ Yes → MINOR (0.x.0)
   └─ Bug fix, docs, polish?
      └─ Yes → PATCH (0.0.x)
```

**Examples:**
- ✅ Slice 19 storage quota guard → **minor** (new feature)
- ✅ Dashboard pagination bug fix → **patch** (fix)
- ✅ Improved logging visibility → **patch** (polish)
- ✅ New embedding provider → **minor** (new capability)
- ❌ Change config format without migration → **major** (breaking)

---

## Retrospective Releases

This project has **15 retrospective releases** (v0.0.1 through v0.11.0) created to document the development history. These were tagged retroactively using the hybrid versioning approach:

- **Major slices/features** → minor version bumps (0.x.0)
- **Polish/enhancements** → patch bumps (0.x.y)

See `CHANGELOG.md` for the complete release history.

---

## Future: Automated Releases via GitHub Actions

**TODO (optional):**
Create `.github/workflows/release.yml` to auto-create releases when version tag is pushed:

```yaml
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create Release
        uses: ncipollo/release-action@v1
        with:
          generateReleaseNotes: true
```

This auto-generates release notes from commits between tags.

---

## Scripts Reference

### `scripts/bump_version.py`

Semantic version bumper (used by `release.sh`):

```bash
./scripts/bump_version.py 0.11.0 minor  # → 0.12.0
./scripts/bump_version.py 0.11.0 patch  # → 0.11.1
./scripts/bump_version.py 0.11.0 major  # → 1.0.0
```

### `scripts/release.sh`

Full release workflow:

```bash
./scripts/release.sh minor  # Bump minor version
./scripts/release.sh patch  # Bump patch version
./scripts/release.sh major  # Bump major version (rare)
```

### `scripts/create_github_releases.sh`

Batch create GitHub releases for all tags (used for retrospective releases):

```bash
./scripts/create_github_releases.sh
```

Requires `gh` CLI authenticated (`gh auth login`).

---

## Troubleshooting

### "Could not find [X.Y.Z] section in CHANGELOG.md"

- Ensure you added the new version section under `## [Unreleased]` in CHANGELOG.md
- Check the version number matches exactly (including brackets: `## [0.12.0]`)
- Ensure there's a blank line before the section

### "Permission denied" when running scripts

```bash
chmod +x scripts/*.sh scripts/*.py
```

### GitHub release creation fails

- Check `gh` CLI is installed: `brew install gh` (macOS)
- Authenticate: `gh auth login`
- Verify repo access: `gh repo view`

### Version in CLI doesn't update

The CLI uses `importlib.metadata.version("rag-params-finder")` which reads from the installed package. After updating `pyproject.toml`, reinstall:

```bash
uv pip install -e .
```

Then verify:

```bash
rag-params-finder version
```
