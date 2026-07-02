#!/bin/bash
# security-scan.sh — security scanners for SCA, SAST, secrets, and containers.
#
# Scanner summary:
#   semgrep      — multi-language SAST (OWASP rules, no API key, needs CLI)
#   osv-scanner  — free SCA via Google OSV DB (no API key, needs CLI)
#   meterian     — SCA + license compliance (API-key-gated: METERIAN_API_TOKEN)
#   trivy        — container/IaC/filesystem scan + SBOM (no API key, needs CLI)
#   trufflehog   — verified secrets in git history (no API key, needs CLI)
#
# Usage:
#   ./scripts/security-scan.sh                  # run all available scanners
#   ./scripts/security-scan.sh --semgrep         # Semgrep only
#   ./scripts/security-scan.sh --osv             # OSV-Scanner only
#   ./scripts/security-scan.sh --meterian        # Meterian only
#   ./scripts/security-scan.sh --trivy           # Trivy only
#   ./scripts/security-scan.sh --trufflehog      # TruffleHog only
#   ./scripts/security-scan.sh --dry-run         # report what would run
#
# API keys (set in ~/.zshrc or ~/.bashrc — never in .env files):
#   export METERIAN_API_TOKEN=<token>   # https://www.meterian.io/account
#
# Returns exit 0  — all active scanners passed
# Returns exit 1  — a scanner found vulnerabilities / issues
# Returns exit 2  — no scanners ran (no CLIs installed, no API keys set)

set -o pipefail

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✅${RESET}  $1"; }
fail() { echo -e "  ${RED}❌${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠️ ${RESET}  $1"; }
info() { echo -e "  ${CYAN}ℹ️ ${RESET}  $1"; }

# ── Flag parsing ──────────────────────────────────────────────────────────────
RUN_SEMGREP=false
RUN_OSV=false
RUN_METERIAN=false
RUN_TRIVY=false
RUN_TRUFFLEHOG=false
DRY_RUN=false
ALL=true

for arg in "$@"; do
  case "$arg" in
    --semgrep)    RUN_SEMGREP=true;    ALL=false ;;
    --osv)        RUN_OSV=true;        ALL=false ;;
    --meterian)   RUN_METERIAN=true;   ALL=false ;;
    --trivy)      RUN_TRIVY=true;      ALL=false ;;
    --trufflehog) RUN_TRUFFLEHOG=true; ALL=false ;;
    --dry-run)    DRY_RUN=true ;;
  esac
done

if $ALL; then
  RUN_SEMGREP=true
  RUN_OSV=true
  RUN_METERIAN=true
  RUN_TRIVY=true
  RUN_TRUFFLEHOG=true
fi

# ── Stack detection ───────────────────────────────────────────────────────────
HAS_PYTHON=false
HAS_NODE=false
HAS_DOCKER=false
HAS_IAC=false

[[ -f "pyproject.toml" || -f ".python-version" || -f "requirements.txt" ]] && HAS_PYTHON=true
[[ -f "package.json" || -f "frontend/package.json" ]]                       && HAS_NODE=true
[[ -f "Dockerfile" || -f "docker-compose.yml" || -f "docker-compose.yaml" ]] && HAS_DOCKER=true
[[ -d "terraform" || -d "infra" || -d "k8s" || -d "helm" ]] \
  || [[ -f "*.tf" ]] 2>/dev/null                                             && HAS_IAC=true

echo ""
echo -e "${BOLD}=== Security Scan ===${RESET}"
echo -e "Mode: $(${DRY_RUN} && echo 'dry-run' || echo 'live')"
$HAS_PYTHON  && echo "  Stack: Python detected"
$HAS_NODE    && echo "  Stack: Node/TS detected"
$HAS_DOCKER  && echo "  Stack: Docker detected"
$HAS_IAC     && echo "  Stack: IaC (Terraform/k8s) detected"
echo ""

SCANS_RUN=0
SCANS_FAILED=0
SCANS_SKIPPED=0

# ─────────────────────────────────────────────────────────────────────────────
# SEMGREP — multi-language SAST
# ─────────────────────────────────────────────────────────────────────────────
if $RUN_SEMGREP; then
  echo -e "${BOLD}--- Semgrep (SAST) ---${RESET}"

  if ! command -v semgrep &>/dev/null; then
    warn "semgrep not installed — brew install semgrep  OR  pip install semgrep"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif $DRY_RUN; then
    info "DRY RUN: would run: semgrep --config=auto --error ."
  else
    SCANS_RUN=$((SCANS_RUN + 1))
    echo "  Running: semgrep (auto ruleset)..."
    # --config=auto pulls Semgrep OSS rules: p/owasp-top-ten, p/python, p/javascript, etc.
    # --error exits 1 if any finding at severity WARNING+
    if ! semgrep --config=auto --error --quiet .; then
      fail "Semgrep found SAST issues"
      SCANS_FAILED=$((SCANS_FAILED + 1))
    else
      ok "Semgrep SAST passed"
    fi
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# OSV-SCANNER — free SCA (Google OSV DB: NVD + GitHub Advisories + OSV)
# ─────────────────────────────────────────────────────────────────────────────
if $RUN_OSV; then
  echo ""
  echo -e "${BOLD}--- OSV-Scanner (SCA) ---${RESET}"

  if ! command -v osv-scanner &>/dev/null; then
    warn "osv-scanner not installed — brew install osv-scanner  OR"
    warn "  go install github.com/google/osv-scanner/cmd/osv-scanner@latest"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif $DRY_RUN; then
    info "DRY RUN: would run: osv-scanner --recursive ."
  else
    SCANS_RUN=$((SCANS_RUN + 1))
    echo "  Running: osv-scanner (recursive lockfile scan)..."
    if ! osv-scanner --recursive .; then
      fail "OSV-Scanner found dependency vulnerabilities"
      SCANS_FAILED=$((SCANS_FAILED + 1))
    else
      ok "OSV-Scanner SCA passed"
    fi
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# METERIAN — SCA + license compliance (API-key-gated)
# ─────────────────────────────────────────────────────────────────────────────
if $RUN_METERIAN; then
  echo ""
  echo -e "${BOLD}--- Meterian (SCA + license) ---${RESET}"

  if [[ -z "$METERIAN_API_TOKEN" ]]; then
    warn "METERIAN_API_TOKEN not set — Meterian scan skipped."
    warn "Add to ~/.zshrc or ~/.bashrc: export METERIAN_API_TOKEN=<your-token>"
    warn "Get token: https://www.meterian.io/account"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif ! command -v docker &>/dev/null; then
    warn "docker not found — Meterian requires Docker (https://docs.docker.com/get-docker/)"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif $DRY_RUN; then
    if $HAS_PYTHON; then
      info "DRY RUN: would run: docker run meterian/cli:latest-python --interactive=false"
    else
      info "DRY RUN: would run: docker run meterian/cli:latest --interactive=false"
    fi
  else
    SCANS_RUN=$((SCANS_RUN + 1))
    # Use latest-python for Python projects — the generic latest is Alpine-based
    # and has glibc incompatibilities with Python runtimes.
    METERIAN_IMAGE="meterian/cli:latest"
    $HAS_PYTHON && METERIAN_IMAGE="meterian/cli:latest-python"

    echo "  Running: Meterian SCA + license ($METERIAN_IMAGE)..."
    set +e
    docker run --rm \
      -e METERIAN_API_TOKEN="$METERIAN_API_TOKEN" \
      -v "$(pwd):/workspace" \
      "$METERIAN_IMAGE" \
      --interactive=false \
      --min-security=90 \
      --min-stability=80
    _met_exit=$?
    set -e

    # Meterian exit code bitmask:
    #   0 = all thresholds met
    #   1 = security score below threshold
    #   2 = stability score below threshold
    #   3 = security + stability both fail (1+2)
    #   4 = licensing fails
    #   negative = system error (auth, network, unsupported) — use --fail-gracefully to pass these
    if [ "$_met_exit" -eq 0 ]; then
      ok "Meterian SCA + license passed"
    elif [ "$_met_exit" -gt 0 ]; then
      fail "Meterian: threshold failure (exit $_met_exit — security=1, stability=2, license=4 bitmask)"
      SCANS_FAILED=$((SCANS_FAILED + 1))
    else
      # Negative exit = system/auth/network error — warn but don't hard-fail the pipeline
      warn "Meterian: system error (exit $_met_exit — auth, network, or unsupported project)"
      warn "  Re-run with --fail-gracefully to suppress system errors in CI"
    fi
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# TRIVY — container / IaC / filesystem / SBOM
# ─────────────────────────────────────────────────────────────────────────────
if $RUN_TRIVY; then
  echo ""
  echo -e "${BOLD}--- Trivy (container / IaC / filesystem) ---${RESET}"

  if ! command -v trivy &>/dev/null; then
    warn "trivy not installed — brew install trivy"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif $DRY_RUN; then
    info "DRY RUN: would run:"
    info "  trivy fs --exit-code 1 --severity HIGH,CRITICAL ."
    $HAS_DOCKER  && info "  trivy image <image> (if built)"
    $HAS_IAC     && info "  trivy config . (IaC misconfigurations)"
  else
    SCANS_RUN=$((SCANS_RUN + 1))
    echo "  Running: trivy filesystem scan..."
    if ! trivy fs --exit-code 1 --severity HIGH,CRITICAL --quiet .; then
      fail "Trivy found HIGH/CRITICAL filesystem vulnerabilities"
      SCANS_FAILED=$((SCANS_FAILED + 1))
    else
      ok "Trivy filesystem scan passed"
    fi

    if $HAS_IAC; then
      echo "  Running: trivy config (IaC misconfigurations)..."
      if ! trivy config --exit-code 1 --severity HIGH,CRITICAL --quiet .; then
        fail "Trivy found IaC misconfigurations"
        SCANS_FAILED=$((SCANS_FAILED + 1))
      else
        ok "Trivy IaC config scan passed"
      fi
    fi
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# TRUFFLEHOG — verified secrets in git history
# ─────────────────────────────────────────────────────────────────────────────
if $RUN_TRUFFLEHOG; then
  echo ""
  echo -e "${BOLD}--- TruffleHog (git history secrets) ---${RESET}"

  if ! command -v trufflehog &>/dev/null; then
    warn "trufflehog not installed — brew install trufflehog"
    SCANS_SKIPPED=$((SCANS_SKIPPED + 1))
  elif $DRY_RUN; then
    info "DRY RUN: would run: trufflehog git file://. --only-verified --no-update"
  else
    SCANS_RUN=$((SCANS_RUN + 1))
    echo "  Running: TruffleHog (verified secrets only, git history)..."
    # --only-verified: skip unverified findings (eliminates most false positives)
    # --no-update: skip auto-update check (for CI reproducibility)
    if ! trufflehog git file://. --only-verified --no-update --fail; then
      fail "TruffleHog found verified secrets in git history"
      SCANS_FAILED=$((SCANS_FAILED + 1))
    else
      ok "TruffleHog: no verified secrets found"
    fi
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}=== Security Scan Summary ===${RESET}"

if $DRY_RUN; then
  info "Dry run complete. Install CLIs and/or set API keys, then re-run without --dry-run."
  exit 0
fi

if [[ $SCANS_SKIPPED -gt 0 && $SCANS_RUN -eq 0 ]]; then
  warn "No scanners ran ($SCANS_SKIPPED skipped — CLIs not installed or API keys absent)."
  warn "Install: semgrep, osv-scanner, trivy, trufflehog  OR  set METERIAN_API_TOKEN."
  exit 2
fi

if [[ $SCANS_FAILED -gt 0 ]]; then
  fail "$SCANS_FAILED scanner(s) found issues. Review findings above."
  exit 1
fi

ok "All active security scanners passed ($SCANS_RUN ran, $SCANS_SKIPPED skipped)."
