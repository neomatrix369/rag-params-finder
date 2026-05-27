# SLICE 20 — Toolchain Hardening (price-analysis + pre-rag patterns)

**MoSCoW:** MUST *(reliability and CI/local parity — prevents regressions before feature slices)*
**Target time:** ~2–3 h
**Status:** ✅ COMPLETE
**Branch:** `chore/slice-20-toolchain-hardening` (merge to `main` when ready)

---

## Goal

Inherit proven hardening patterns from **price-analysis** and **pre-rag-explorer-dashboard** so `rag-params-finder` reaches **Serious** maturity: one command runs the same gates as CI, coverage is enforced on tested modules, frontend lint is wired, Python SCA runs in CI, and repo hygiene is consistent across editors and agents.

**Maturity profile:** Serious (10–12 tools)
**20-Factor compliance:** Factor 2 (Dependencies), Factor 3 (Config), Factor 14 (Telemetry via integrity script)

---

## Source analysis

| Pattern | Source repo | Adopt? |
|---------|-------------|--------|
| `scripts/quality-gates.sh` mirroring CI | pre-rag | ✅ |
| Baseline-first coverage threshold (not aspirational) | pre-rag | ✅ |
| `.gitleaks.toml` domain allowlists | pre-rag | ✅ |
| Dependabot (pip, npm, actions) | pre-rag | ✅ |
| ESLint + `eslint-plugin-security` | pre-rag | ✅ |
| `.nvmrc` / `.editorconfig` / `.gitattributes` | pre-rag | ✅ |
| `scripts/check_integrity.py` (unit + import smoke) | price-analysis | ✅ |
| pytest `integration` / `slow` markers | price-analysis | ✅ |
| `pip-audit` in CI | governance (Serious tier) | ✅ |
| Husky + lint-staged | pre-rag | ❌ — pre-commit already covers Python + frontend |
| Xenon complexity gates | price-analysis | ❌ — defer until legacy debt warrants scoped gates |
| Vitest frontend tests | pre-rag | ❌ — separate slice when UI test tier is planned |
| Torch/transformers major upgrade | pip-audit findings | ❌ — tracked via `scripts/pip-audit.sh` ignores |
| `scripts/repo-lint.sh` (shellcheck, actionlint, markdownlint) | governance (Serious tier) | ✅ *(2026-05-27 follow-on)* |
| `install-git-hooks.sh` + pre-push essential checks (`--all-files`) | governance | ✅ *(2026-05-27 follow-on)* |
| yamllint / stylelint / markdown “strict” rules | governance | ❌ — `check-yaml` + pragmatic `.markdownlint.json` suffice for now |

---

## Acceptance criteria

### Scripts & local gates
- [x] `./scripts/quality-gates.sh` passes (mirrors `.github/workflows/ci.yml`, including repo lint as step 1)
- [x] `./scripts/quality-gates.sh --full` runs local gitleaks + `pre-commit run --all-files` (default mode already includes `pip-audit.sh`)
- [x] `bash scripts/repo-lint.sh` passes (shellcheck, actionlint, markdownlint)
- [x] `python scripts/check_integrity.py` passes (unit tests + import smoke)

### CI
- [x] **Repo-lint job:** shellcheck (`scripts/*.sh`) → actionlint (workflows) → markdownlint (`*.md`, `.markdownlint.json`)
- [x] Backend job: ruff → format check → mypy → **bandit** → pytest + **80% coverage** → `pip-audit.sh`
- [x] Frontend job: **eslint** → typecheck → build → npm audit (high+)
- [x] **Secrets job:** gitleaks-action with `.gitleaks.toml`
- [x] Node from `.nvmrc`; Python from `.python-version`

### Pre-commit
- [x] Gitleaks uses `.gitleaks.toml`
- [x] Frontend eslint hook on `frontend/**/*.{ts,tsx}`
- [x] Bandit hook (medium+ via `uv run bandit … -ll`, same as CI)
- [x] Shellcheck on `scripts/*.sh` (`shellcheck-py`)
- [x] Actionlint on `.github/workflows`
- [x] Markdownlint on `*.md` (excludes `.claude/`)
- [x] Pre-push hook runs same essential checks as commit on all files (`pre-commit run --all-files`)

### Coverage scope (baseline-first)
Measured baseline **83.6%** on:

- `server/core/search_index_plan.py`
- `server/core/search_index_guard.py`
- `server/core/results_analyzer.py`
- `server/models/config.py`

Threshold set to **80%** (`--cov-fail-under=80` in CI and quality-gates).

### Security
- [x] `bash scripts/pip-audit.sh` passes (fixable deps upgraded via `[tool.uv] override-dependencies`)
- [x] ML transitive vulns (torch/transformers) documented + ignored until major upgrade slice
- [x] `npm audit --audit-level=high` passes in CI

### Docs
- [x] `docs/contributor-guide/development.md` — quality gates section updated
- [x] `CLAUDE.md` — verify-all commands + baseline metrics updated
- [x] `docs/slices/PROGRESS.md` — slice 20 row + decision log entry

---

## Files in scope

### Created
| File | Purpose |
|------|---------|
| `scripts/quality-gates.sh` | Unified local gates (mirrors CI) |
| `scripts/check_integrity.py` | Unit tests + import smoke; `--full` optional |
| `scripts/pip-audit.sh` | Python SCA with ML-stack ignore list |
| `.gitleaks.toml` | Secret-scan allowlists |
| `.nvmrc` | Node 22 pin |
| `.editorconfig` | Cross-editor formatting |
| `.gitattributes` | Line endings + lockfile diff hygiene |
| `.github/dependabot.yml` | Weekly pip/npm/actions updates |
| `frontend/.eslintrc.cjs` | ESLint + security plugin |
| `docs/slices/SLICE-20-TOOLCHAIN-HARDENING.md` | This spec |
| `scripts/repo-lint.sh` | Shell + workflow + Markdown linters (pre-commit wrappers) |
| `scripts/install-git-hooks.sh` | Installs pre-commit + pre-push hooks |
| `.markdownlint.json` | Pragmatic Markdown rules for existing docs |

### Modified
| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Coverage, eslint, pip-audit, .nvmrc; **`repo-lint` job** |
| `.pre-commit-config.yaml` | gitleaks, frontend lint, **shellcheck / actionlint / markdownlint** |
| `scripts/quality-gates.sh` | Step 1/11 repo lint; renumbered steps |
| `scripts/push_tags_incrementally.sh` | Shellcheck quote fix |
| `scripts/release.sh` | Shellcheck `read -r` |
| `pyproject.toml` | Coverage config, pytest markers, uv overrides, bandit/pip-audit dev deps |
| `uv.lock` | Dependency overrides |
| `frontend/package.json` / `package-lock.json` | eslint-plugin-security |
| `frontend/src/components/*.tsx` | ESLint fixes (unsafe finally, deps, security FP) |
| `frontend/src/services/fetchWithProgress.ts` | Stream loop lint fix |
| `docs/contributor-guide/development.md` | Gate commands + baselines |
| `CLAUDE.md` | Verify-all + baseline |
| `docs/slices/PROGRESS.md` | Slice 20 status |

---

## Verification commands

```bash
# Primary exit gate (includes repo lint)
./scripts/quality-gates.sh

# Repo lint only (shell + workflows + Markdown)
bash scripts/repo-lint.sh

# Integrity smoke
python scripts/check_integrity.py

# Full local audit (optional before merge)
./scripts/quality-gates.sh --full
```

**Expected (2026-05-27 baseline):**

| Gate | Result |
|------|--------|
| `bash scripts/repo-lint.sh` | shellcheck + actionlint + markdownlint pass |
| `ruff check .` | 0 errors |
| `mypy server/ cli/` | 0 errors |
| `pytest` | 23 passed, 83.6% scoped coverage |
| `npm run lint` | 0 errors, 0 warnings |
| `npm run build` | ~49 modules |
| `bash scripts/pip-audit.sh` | 0 unfixed vulns (16 ML ignores) |
| `npm audit --audit-level=high` | 0 high |

---

## Pragmatic decisions

### 1. Scoped coverage, not whole-repo
**Decision:** Enforce 80% on four unit-tested modules only, not `server/` + `cli/` (28% whole-repo).
**Rationale:** pre-rag pattern — measure baseline first, set threshold at baseline − margin. Avoids disabling coverage gate or aspirational 75% on untested pipeline code.

### 2. pip-audit ML ignores
**Decision:** `scripts/pip-audit.sh` ignores 16 torch/transformers CVEs; upgraded urllib3, starlette, idna, langchain-core via uv overrides.
**Rationale:** sentence-transformers pins old torch; major ML bump is a separate slice with integration risk.

### 3. pre-commit over Husky
**Decision:** Extend existing pre-commit rather than add Husky/lint-staged.
**Rationale:** Python-first repo already uses pre-commit for ruff/mypy/gitleaks; duplicating hooks adds drift.

### 4. ESLint security false positives
**Decision:** Inline `eslint-disable-next-line security/detect-object-injection` for typed union props (StatCard, MethodBadge).
**Rationale:** Keys are TypeScript unions, not user input — matches pre-rag Slice 2 approach.

### 5. Branch from `main`
**Decision:** Slice branch targets `main`, not in-flight code-review-graph work.
**Rationale:** Toolchain hardening is independent; keeps PR reviewable and revertable.

### 6. Pragmatic markdownlint config
**Decision:** `.markdownlint.json` disables noisy style rules (MD032, MD040, etc.) so legacy docs pass without a mass reformat.
**Rationale:** Catch structural issues and regressions; tighten rules incrementally if desired.

### 7. shellcheck-py over koalaman/shellcheck-precommit
**Decision:** Use `shellcheck-py` pre-commit repo (no Docker).
**Rationale:** `koalaman/shellcheck-precommit` rev failed in CI; pip wheel hook matches Serious tier without Docker.

### 8. Pre-push mirrors commit essential checks, not full gates
**Decision:** Pre-push runs `pre-commit run --all-files` (same hooks as commit, whole repo); full `quality-gates.sh` stays manual + CI on PR.
**Rationale:** Matches “essential checks like commit”; pytest, coverage, and dependency audits stay in CI / pre-PR script.

---

## Deferred → future slices

| Item | Suggested slice |
|------|-----------------|
| Torch/transformers upgrade + clear pip-audit ignores | Slice 21 or deps slice |
| `slow-tests/` integration tier (MongoDB mocks) | Test suite expansion |
| Xenon complexity gates (scoped, price-analysis pattern) | Optional polish |
| Vitest frontend tests | Dashboard test slice |
| CodeQL / Trivy workflows | Optimal maturity tier |
| Bandit low-severity cleanup (B110/B112/B603 in metadata) | Optional polish |

---

## Cross-check matrix (2026-05-27)

Three-way comparison after inheriting patterns from **price-analysis** and **pre-rag-explorer-dashboard**.

| Pattern | price-analysis | pre-rag | rag-params-finder (post slice 20) |
|---------|----------------|---------|-------------------------------------|
| Unified `quality-gates.sh` | ❌ | ✅ `--quick`/`--full` | ✅ aligned with pre-rag |
| CI mirrors local script | ❌ (CI = pytest only) | ✅ | ✅ |
| gitleaks pre-commit | ❌ | ✅ Husky + optional | ✅ pre-commit |
| gitleaks in CI | ❌ | ✅ gitleaks-action | ✅ secrets job |
| pip-audit / npm audit | ❌ | ✅ npm only | ✅ both |
| bandit SAST | ✅ pre-commit | ❌ | ✅ CI + pre-commit (`-ll`) |
| ESLint + security plugin | N/A | ✅ | ✅ |
| Coverage fail-under | ❌ | ✅ 40% services | ✅ 80% scoped Python modules |
| Dependabot | ❌ | ✅ | ✅ pip + npm + actions |
| `.editorconfig` / `.gitattributes` | ❌ | ✅ editorconfig | ✅ both |
| `.nvmrc` + CI Node pin | N/A | ✅ | ✅ |
| `check_integrity.py` | ✅ | ❌ | ✅ |
| pytest integration/slow markers | ✅ | N/A (vitest) | ✅ (markers defined) |
| pre-commit (Python framework) | ✅ heavy | ✅ Serious-lite | ✅ |
| shellcheck / actionlint / markdownlint | partial | partial | ✅ repo-lint job + hooks |
| pre-push essential checks | ❌ | partial (husky) | ✅ `pre-commit --all-files` |
| Husky + lint-staged | ❌ | ✅ | ❌ (pre-commit instead) |
| Prettier | ✅ black/isort | ✅ | ❌ (ruff + eslint) |
| Xenon complexity | ✅ scoped | ❌ | ❌ deferred |
| Characterization tests | ✅ | ❌ | ❌ (unit tests only) |
| Docker healthchecks | ✅ | ❌ | ✅ Slice 14 |
| Release script | ❌ | ❌ | ✅ `scripts/release.sh` |
| ADR + slice governance | partial | ✅ | ✅ |
| CodeQL / Trivy | ❌ | ❌ deferred | ❌ deferred |

**Verdict:** rag-params-finder now combines the strongest elements of both references — pre-rag's CI/local parity, secrets scanning in CI, and baseline-first coverage; price-analysis's integrity script and bandit — while keeping its own strengths (uv, ruff, semver release script, Python+React monorepo pre-commit).

---

## Commit message

```
chore(ci): slice 20 toolchain hardening from reference repos

- Add quality-gates.sh, check_integrity.py, pip-audit.sh, repo-lint.sh, install-git-hooks.sh
- CI: repo-lint job; coverage 80% on scoped modules; eslint; pip-audit
- Git hooks: pre-commit + pre-push (essential checks on all files); shellcheck, actionlint, markdownlint
- Wire .gitleaks.toml, .nvmrc, dependabot, repo hygiene files
- Upgrade urllib3/starlette/idna/langchain-core; document ML transitive audit ignores

Refs: price-analysis, pre-rag-explorer-dashboard toolchain patterns
```
