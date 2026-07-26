# Handoff — 2026-07-26

## Where We Are

**36** ✅ COMPLETE (Postgres catalog preflight + four-value `storage_mode`, branch `slice/36-postgres-preflight-stats`). **35** ✅ / **43** ✅. Next Must = **37**. Parallel gate track: **32** 🔨 / **32C** 📋 / **32B** 📋 · **33** 🔨 (implementation largely landed; after-checks remain).

## What's Done (recent)

- Slice 36 — Postgres index preflight + db-stats `storage_mode` — ✅ COMPLETE (`gate-evidence/slice-36.json`)
- Slice 43 — Supabase example-config verification — ✅ COMPLETE (`gate-evidence/slice-43.json`)
- Slice 35 — Postgres sparse + hybrid RRF — ✅ COMPLETE (`gate-evidence/slice-35.json`)
- Slice 34 — Postgres dense retrieval — ✅ COMPLETE
- Storage refactor — Mongo/Postgres boundaries + contract suite (PR #113)
- Canonical `STORAGE_BACKEND=mongodb` (legacy `mongo` alias)

## What's Next

- **Slice 37** — `--mongodb|postgres-local|cloud` flags, hosted `ensure_env`, config↔server 422, Path B docs (`SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md`)
  - Also owns: `database_provider` normalize `supabase`→`postgres`, compose profile spelling vs mode tokens, `configs/supabase/` naming backlog
- Then **38** → **22**

## Blockers / Open Questions

- 32C/32B after-checks still open on the Protocol gate track (do not block 37)
- Vocabulary leftovers (YAML `supabase` label, compose `local-postgres`) deferred to 37 — not Slice 36 regressions

## Context for Next Session

- Spec SSOT: `docs/plan/slices/SLICE-37-POSTGRES-LOCAL-CLOUD-PARITY.md`
- Prior evidence: `docs/plan/gate-evidence/slice-36.json`
- Abstraction reminder: engine (`STORAGE_BACKEND`) × location (`storage_mode`); Atlas/Supabase = cloud shorthand only
